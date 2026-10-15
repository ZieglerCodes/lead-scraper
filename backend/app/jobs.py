"""Development-only background tasks. Replace with a durable worker before production."""
import logging
from pathlib import Path
from app import storage as db
from app.services.pipeline import demo_search, import_csv

log = logging.getLogger(__name__)


def run_demo_job(owner_id: str, job_id: str, query: str, location: str, max_results: int) -> None:
    try:
        db.set_job(owner_id, job_id, "running")
        leads = demo_search(query, location, max_results)
        db.insert_leads(owner_id, job_id, leads)
        db.set_job(owner_id, job_id, "completed", found=len(leads), message="Synthetic sample data only")
    except Exception:
        log.exception("Demo job failed: %s", job_id)
        db.set_job(owner_id, job_id, "failed", message="Internal job error; see server logs")


def run_import_job(owner_id: str, job_id: str, upload_path: str) -> None:
    path = Path(upload_path)
    try:
        db.set_job(owner_id, job_id, "running")
        leads = import_csv(path.read_bytes())
        db.insert_leads(owner_id, job_id, leads)
        db.set_job(owner_id, job_id, "completed", found=len(leads), message="Imported user-supplied CSV")
    except ValueError as exc:
        db.set_job(owner_id, job_id, "failed", message=str(exc)[:250])
    except Exception:
        log.exception("CSV import failed: %s", job_id)
        db.set_job(owner_id, job_id, "failed", message="Internal job error; see server logs")
    finally:
        path.unlink(missing_ok=True)
