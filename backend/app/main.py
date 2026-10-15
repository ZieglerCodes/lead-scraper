"""Phase 4: authenticated API with PostgreSQL queue in production."""
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from app import storage as db
from app.auth import current_user, supabase_url
from app.jobs import run_demo_job, run_import_job
from app.schemas import SearchRequest

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "data" / "uploads"
User = Annotated[str, Depends(current_user)]


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.environ.get("DEPLOYMENT_MODE") == "production":
        if not db.is_postgres():
            raise RuntimeError("Production requires PostgreSQL DATABASE_URL; refusing local SQLite")
        supabase_url()  # Refuse production startup without the trusted issuer.
        allowed = os.environ.get("FRONTEND_ORIGINS", "")
        if not allowed or "*" in allowed:
            raise RuntimeError("Production requires explicit FRONTEND_ORIGINS")
    db.init_db()
    yield


app = FastAPI(
    title="Lead Scraper Backend — Phase 4",
    description="Authenticated development backend. Synthetic searches and authorized CSV imports only.",
    version="0.4.0",
    lifespan=lifespan,
)
origins = [v.strip() for v in os.environ.get("FRONTEND_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",") if v.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health")
def health():
    # Intentionally public for connection diagnostics; contains no private data.
    try:
        db.ping()
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return {"status": "ok", "phase": 4, "authentication": "Supabase JWT required",
            "storage": "PostgreSQL" if db.is_postgres() else "Local SQLite",
            "processing": "durable worker" if db.is_postgres() else "local background tasks"}


@app.get("/api/me")
def me(owner_id: User):
    return {"id": owner_id}


@app.post("/api/jobs/search", status_code=202)
def search(request: SearchRequest, background_tasks: BackgroundTasks, owner_id: User):
    try:
        job = db.create_job(owner_id, "search-demo", request.query, request.location, request.max_results)
    except ValueError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    if not db.is_postgres():
        background_tasks.add_task(run_demo_job, owner_id, job["id"], request.query, request.location, request.max_results)
    return job


@app.post("/api/jobs/import", status_code=202)
async def import_leads(background_tasks: BackgroundTasks, owner_id: User, file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Upload a .csv file")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    if not content:
        raise HTTPException(status_code=400, detail="CSV is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Maximum CSV size is 2 MB")
    # In production, store the upload payload transactionally in PostgreSQL.
    # It is processed and deleted by the worker; ephemeral Render disks are not used.
    if db.is_postgres():
        try:
            return db.create_job(owner_id, "csv-import", None, None, 0, csv_bytes=content)
        except ValueError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = UPLOAD_DIR / f"{uuid.uuid4().hex}.csv"
    temp_path.write_bytes(content)
    try:
        job = db.create_job(owner_id, "csv-import", None, None, 0)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    background_tasks.add_task(run_import_job, owner_id, job["id"], str(temp_path))
    return job


@app.get("/api/jobs")
def jobs(owner_id: User):
    return {"jobs": db.list_jobs(owner_id)}


@app.get("/api/jobs/{job_id}")
def job_detail(job_id: str, owner_id: User):
    job = db.get_job(owner_id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/jobs/{job_id}/leads")
def job_leads(job_id: str, owner_id: User, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    job = db.get_job(owner_id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "status": job["status"], "leads": db.get_leads(owner_id, job_id, limit, offset)}
