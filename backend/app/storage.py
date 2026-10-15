"""Select SQLite for local Phase 3 compatibility, PostgreSQL for deployment."""
import os
from app import db as sqlite
from app import postgres


def is_postgres():
    return bool(os.environ.get('DATABASE_URL','').strip())


def provider():
    return postgres if is_postgres() else sqlite


def init_db():
    return provider().init_db()


def ping():
    if is_postgres():
        postgres.ping()
    else:
        with sqlite.connect() as conn:
            conn.execute('SELECT 1').fetchone()


def create_job(owner_id, kind, query, location, requested, *, csv_bytes=None):
    if is_postgres():
        return postgres.create_job(owner_id,kind,query,location,requested,csv_bytes=csv_bytes)
    return sqlite.create_job(owner_id,kind,query,location,requested)


def get_job(*args, **kwargs):
    return provider().get_job(*args, **kwargs)


def list_jobs(*args, **kwargs):
    return provider().list_jobs(*args, **kwargs)


def get_leads(*args, **kwargs):
    return provider().get_leads(*args, **kwargs)


def set_job(*args, **kwargs):
    return provider().set_job(*args, **kwargs)


def insert_leads(*args, **kwargs):
    return provider().insert_leads(*args, **kwargs)
