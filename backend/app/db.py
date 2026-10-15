"""Local SQLite persistence with mandatory user ownership constraints.

Existing Phase 2 records migrate to a quarantined, unclaimable owner rather
than being visible to whichever real account signs in first.
"""
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

LEGACY_OWNER = "__phase2_unclaimed__"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def database_path() -> Path:
    default = Path(__file__).resolve().parents[1] / "data" / "lead_scraper.sqlite3"
    return Path(os.environ.get("LEAD_SCRAPER_DATABASE_PATH", str(default)))


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                query TEXT,
                location TEXT,
                requested INTEGER NOT NULL DEFAULT 0,
                found INTEGER NOT NULL DEFAULT 0,
                message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                name TEXT,
                address TEXT,
                phone TEXT,
                email TEXT,
                website TEXT,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        # Backward-compatible schema upgrade. NEVER assign legacy records to a
        # newly registered user; those records remain inaccessible through API.
        for table in ("jobs", "leads"):
            columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            if "owner_id" not in columns:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN owner_id TEXT NOT NULL DEFAULT '{LEGACY_OWNER}'")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_jobs_owner_created ON jobs(owner_id, created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_leads_owner_job ON leads(owner_id, job_id)")
        conn.execute("""UPDATE jobs SET status='failed', message='Server restarted during job; retry', updated_at=?
                     WHERE status IN ('queued', 'running')""", (_utc_now(),))


def create_job(owner_id: str, kind: str, query: str | None, location: str | None, requested: int) -> dict:
    job_id = str(uuid.uuid4())
    now = _utc_now()
    with connect() as conn:
        conn.execute("""INSERT INTO jobs (id, owner_id, kind, status, query, location, requested, created_at, updated_at)
                        VALUES (?, ?, ?, 'queued', ?, ?, ?, ?, ?)""", (job_id, owner_id, kind, query, location, requested, now, now))
    return get_job(owner_id, job_id)


def set_job(owner_id: str, job_id: str, status: str, *, found: int | None = None, message: str | None = None) -> None:
    with connect() as conn:
        conn.execute("""UPDATE jobs SET status=?, found=COALESCE(?, found), message=?, updated_at=?
                        WHERE id=? AND owner_id=?""", (status, found, message, _utc_now(), job_id, owner_id))


def get_job(owner_id: str, job_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id=? AND owner_id=?", (job_id, owner_id)).fetchone()
    return dict(row) if row else None


def list_jobs(owner_id: str, limit: int = 50) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM jobs WHERE owner_id=? ORDER BY created_at DESC, id DESC LIMIT ?", (owner_id, limit)).fetchall()
    return [dict(row) for row in rows]


def insert_leads(owner_id: str, job_id: str, leads: list[dict]) -> None:
    now = _utc_now()
    with connect() as conn:
        # Prevent inserting into another owner's job even inside workers.
        job = conn.execute("SELECT 1 FROM jobs WHERE id=? AND owner_id=?", (job_id, owner_id)).fetchone()
        if not job:
            raise ValueError("Job not found")
        conn.executemany("""INSERT INTO leads (id, owner_id, job_id, name, address, phone, email, website, source, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            (str(uuid.uuid4()), owner_id, job_id, lead["name"], lead["address"], lead["phone"], lead["email"], lead["website"], lead["source"], now)
            for lead in leads
        ])


def get_leads(owner_id: str, job_id: str, limit: int = 100, offset: int = 0) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("""SELECT leads.id, leads.name, leads.address, leads.phone, leads.email,
                                      leads.website, leads.source, leads.created_at
                               FROM leads JOIN jobs ON jobs.id = leads.job_id
                               WHERE leads.job_id=? AND leads.owner_id=? AND jobs.owner_id=?
                               ORDER BY leads.created_at, leads.id LIMIT ? OFFSET ?""",
                            (job_id, owner_id, owner_id, limit, offset)).fetchall()
    return [dict(row) for row in rows]
