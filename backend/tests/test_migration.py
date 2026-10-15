import sqlite3
from app import db
from conftest import USER_A


def test_phase2_rows_quarantined(tmp_path, monkeypatch):
    path = tmp_path / 'existing.sqlite3'
    monkeypatch.setenv('LEAD_SCRAPER_DATABASE_PATH', str(path))
    with sqlite3.connect(path) as conn:
        conn.executescript('''
            CREATE TABLE jobs (id TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL, query TEXT, location TEXT,
                requested INTEGER NOT NULL DEFAULT 0, found INTEGER NOT NULL DEFAULT 0, message TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE leads (id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                name TEXT, address TEXT, phone TEXT, email TEXT, website TEXT, source TEXT NOT NULL, created_at TEXT NOT NULL);
            INSERT INTO jobs VALUES ('old-job', 'csv-import','completed',null,null,0,1,null,'2026','2026');
            INSERT INTO leads VALUES ('old-lead','old-job','Legacy Corp',null,null,null,null,'csv','2026');
        ''')
    db.init_db()
    assert db.get_job(USER_A, 'old-job') is None
    assert db.list_jobs(USER_A) == []
    assert db.get_leads(USER_A, 'old-job') == []
    with db.connect() as conn:
        assert conn.execute("SELECT owner_id FROM jobs WHERE id='old-job'").fetchone()[0] == db.LEGACY_OWNER
        assert conn.execute("SELECT owner_id FROM leads WHERE id='old-lead'").fetchone()[0] == db.LEGACY_OWNER
    new = db.create_job(USER_A, 'search-demo', 'roofing', 'Houston', 1)
    assert db.get_job(USER_A, new['id']) is not None
