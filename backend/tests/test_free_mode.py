"""Free hosting adds in-process work only when explicitly configured."""
from app import storage
from conftest import USER_A


def test_free_mode_processes_postgres_demo(client, headers, monkeypatch):
    from app import main
    called = []
    monkeypatch.setenv("LEAD_SCRAPER_JOB_MODE", "inprocess")
    monkeypatch.setattr(storage, "is_postgres", lambda: True)
    monkeypatch.setattr(storage, "create_job", lambda *a, **kw: {"id": "job1", "status": "queued"})
    monkeypatch.setattr(main, "process_one", lambda job_id: called.append(job_id))
    response = client.post("/api/jobs/search", json={"query": "roofers", "location": "Houston", "max_results": 2}, headers=headers(USER_A))
    assert response.status_code == 202
    assert called == ["job1"]


def test_free_mode_processes_postgres_import(client, headers, monkeypatch):
    from app import main
    called = []
    monkeypatch.setenv("LEAD_SCRAPER_JOB_MODE", "inprocess")
    monkeypatch.setattr(storage, "is_postgres", lambda: True)
    monkeypatch.setattr(storage, "create_job", lambda *a, **kw: {"id": "job2", "status": "queued"})
    monkeypatch.setattr(main, "process_one", lambda job_id: called.append(job_id))
    response = client.post("/api/jobs/import", files={"file": ("leads.csv", b"Name,Phone\nTest,7135550101", "text/csv")}, headers=headers(USER_A))
    assert response.status_code == 202
    assert called == ["job2"]


def test_free_mode_does_not_trigger_when_disabled(client, headers, monkeypatch):
    from app import main
    called = []
    monkeypatch.delenv("LEAD_SCRAPER_JOB_MODE", raising=False)
    monkeypatch.setattr(storage, "is_postgres", lambda: True)
    monkeypatch.setattr(storage, "create_job", lambda *a, **kw: {"id": "job3", "status": "queued"})
    monkeypatch.setattr(main, "process_one", lambda job_id: called.append(job_id))
    response = client.post("/api/jobs/search", json={"query": "roofers", "location": "Houston", "max_results": 2}, headers=headers(USER_A))
    assert response.status_code == 202
    assert called == []
