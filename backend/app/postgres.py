"""Production PostgreSQL storage with per-account access and durable job payloads.

The server never uses the client's owner_id. The owner is obtained from a
verified Supabase JWT in the API dependency.
"""
import os
import uuid
from datetime import datetime, timezone



def connect():
    url = os.environ.get('DATABASE_URL', '').strip()
    if not url:
        raise RuntimeError('DATABASE_URL is required for PostgreSQL')
    # Lazy import also keeps the existing SQLite-only local tests runnable.
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(url, connect_timeout=10, row_factory=dict_row)


def init_db():
    with connect() as conn:
        conn.execute('''
          CREATE TABLE IF NOT EXISTS jobs (
            id UUID PRIMARY KEY, owner_id UUID NOT NULL,
            kind TEXT NOT NULL CHECK (kind IN ('search-demo', 'csv-import')),
            status TEXT NOT NULL CHECK (status IN ('queued','running','completed','failed')),
            query TEXT, location TEXT, requested INTEGER NOT NULL DEFAULT 0,
            found INTEGER NOT NULL DEFAULT 0, message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
          )''')
        conn.execute('''
          CREATE TABLE IF NOT EXISTS leads (
            id UUID PRIMARY KEY, owner_id UUID NOT NULL,
            job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            name TEXT, address TEXT, phone TEXT, email TEXT, website TEXT,
            source TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
          )''')
        conn.execute('''
          CREATE TABLE IF NOT EXISTS job_payloads (
            job_id UUID PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
            csv_bytes BYTEA NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
          )''')
        conn.execute('CREATE INDEX IF NOT EXISTS ix_jobs_owner_created ON jobs(owner_id, created_at DESC)')
        conn.execute('CREATE INDEX IF NOT EXISTS ix_jobs_queue ON jobs(created_at) WHERE status = \'queued\'')
        conn.execute('CREATE INDEX IF NOT EXISTS ix_leads_owner_job ON leads(owner_id, job_id)')


def _serialize(row):
    if row is None:
        return None
    return {k: (str(v) if isinstance(v, (uuid.UUID, datetime)) else v) for k,v in dict(row).items()}


def _serialize_all(rows):
    return [_serialize(r) for r in rows]


def ping():
    with connect() as conn:
        conn.execute('SELECT 1').fetchone()


def create_job(owner_id, kind, query, location, requested, csv_bytes=None):
    # Coarse per-account production guard against accidental or abusive job spam.
    # No billing or metering system is offered by this MVP.
    owner_id = str(uuid.UUID(str(owner_id)))
    job_id = uuid.uuid4()
    with connect() as conn:
        # Serialize the quota check for a single account within this transaction.
        conn.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (owner_id,))
        daily = conn.execute("SELECT COUNT(*) AS n FROM jobs WHERE owner_id=%s AND created_at >= NOW() - INTERVAL '24 hours'", (owner_id,)).fetchone()['n']
        active = conn.execute("SELECT COUNT(*) AS n FROM jobs WHERE owner_id=%s AND status IN ('queued','running')", (owner_id,)).fetchone()['n']
        if daily >= 30 or active >= 3:
            raise ValueError('Job limit reached: maximum 30 per 24 hours and 3 active jobs per account')
        conn.execute('''INSERT INTO jobs (id,owner_id,kind,status,query,location,requested)
                        VALUES (%s,%s,%s,'queued',%s,%s,%s)''', (job_id,owner_id,kind,query,location,requested))
        if csv_bytes is not None:
            conn.execute('INSERT INTO job_payloads (job_id,csv_bytes) VALUES (%s,%s)', (job_id, csv_bytes))
    return get_job(owner_id,str(job_id))


def set_job(owner_id, job_id, status, *, found=None, message=None):
    with connect() as conn:
        conn.execute('''UPDATE jobs SET status=%s, found=COALESCE(%s,found), message=%s, updated_at=NOW()
                        WHERE id=%s AND owner_id=%s''', (status,found,message,uuid.UUID(job_id),uuid.UUID(owner_id)))


def get_job(owner_id, job_id):
    try:
        parsed_id = uuid.UUID(job_id)
    except (ValueError, AttributeError):
        return None
    with connect() as conn:
        row = conn.execute('SELECT * FROM jobs WHERE id=%s AND owner_id=%s', (parsed_id,uuid.UUID(owner_id))).fetchone()
    return _serialize(row)


def list_jobs(owner_id, limit=50):
    with connect() as conn:
        rows = conn.execute('SELECT * FROM jobs WHERE owner_id=%s ORDER BY created_at DESC, id DESC LIMIT %s', (uuid.UUID(owner_id),limit)).fetchall()
    return _serialize_all(rows)


def get_leads(owner_id, job_id, limit=100, offset=0):
    try:
        parsed_id = uuid.UUID(job_id)
    except (ValueError, AttributeError):
        return []
    with connect() as conn:
        rows = conn.execute('''SELECT leads.id, leads.name, leads.address, leads.phone, leads.email,
                    leads.website, leads.source, leads.created_at FROM leads
                    JOIN jobs ON jobs.id=leads.job_id
                    WHERE leads.job_id=%s AND leads.owner_id=%s AND jobs.owner_id=%s
                    ORDER BY leads.created_at,leads.id LIMIT %s OFFSET %s''',
                    (parsed_id,uuid.UUID(owner_id),uuid.UUID(owner_id),limit,offset)).fetchall()
    return _serialize_all(rows)


def claim_next_job():
    """Exactly one worker can claim a queued job. Stale running jobs fail safely."""
    with connect() as conn:
        conn.execute('''UPDATE jobs SET status='failed', message='Worker interrupted; resubmit this job', updated_at=NOW()
                        WHERE status='running' AND updated_at < NOW() - INTERVAL '15 minutes' ''')
        conn.execute('DELETE FROM job_payloads WHERE job_id IN (SELECT id FROM jobs WHERE status = \'failed\')')
        row = conn.execute('''SELECT id, owner_id, kind, query, location, requested
                              FROM jobs WHERE status='queued' ORDER BY created_at,id
                              FOR UPDATE SKIP LOCKED LIMIT 1''').fetchone()
        if row is None:
            return None
        conn.execute("UPDATE jobs SET status='running',updated_at=NOW() WHERE id=%s", (row['id'],))
        if row['kind'] == 'csv-import':
            payload = conn.execute('SELECT csv_bytes FROM job_payloads WHERE job_id=%s', (row['id'],)).fetchone()
            row['csv_bytes'] = bytes(payload['csv_bytes']) if payload else None
        return _serialize(row)


def finish_job(owner_id, job_id, leads, message):
    with connect() as conn:
        job = conn.execute("SELECT status FROM jobs WHERE id=%s AND owner_id=%s FOR UPDATE", (job_id,owner_id)).fetchone()
        if not job or job['status'] != 'running':
            raise RuntimeError('Job not owned or not running')
        conn.executemany('''INSERT INTO leads (id,owner_id,job_id,name,address,phone,email,website,source)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)''', [
            (uuid.uuid4(),owner_id,job_id,lead['name'],lead['address'],lead['phone'],lead['email'],lead['website'],lead['source'])
            for lead in leads
        ])
        conn.execute("UPDATE jobs SET status='completed',found=%s,message=%s,updated_at=NOW() WHERE id=%s AND owner_id=%s",
                     (len(leads),message,job_id,owner_id))
        conn.execute('DELETE FROM job_payloads WHERE job_id=%s', (job_id,))


def fail_job(owner_id, job_id, message):
    with connect() as conn:
        conn.execute("UPDATE jobs SET status='failed',message=%s,updated_at=NOW() WHERE id=%s AND owner_id=%s AND status='running'",
                     (message[:250],job_id,owner_id))
        conn.execute('DELETE FROM job_payloads WHERE job_id=%s', (job_id,))


def claim_job(job_id):
    # Atomically claim one job for the free-tier API's background task.
    try:
        parsed_id = uuid.UUID(str(job_id))
    except (ValueError, TypeError, AttributeError):
        return None
    with connect() as conn:
        row = conn.execute("SELECT id, owner_id, kind, query, location, requested FROM jobs WHERE id=%s AND status='queued' FOR UPDATE SKIP LOCKED", (parsed_id,)).fetchone()
        if row is None:
            return None
        conn.execute("UPDATE jobs SET status='running', updated_at=NOW() WHERE id=%s", (parsed_id,))
        if row['kind'] == 'csv-import':
            payload = conn.execute('SELECT csv_bytes FROM job_payloads WHERE job_id=%s', (parsed_id,)).fetchone()
            row['csv_bytes'] = bytes(payload['csv_bytes']) if payload else None
        return _serialize(row)
