from app import worker


def test_worker_claims_demo_and_completes(monkeypatch):
    claimed = [{'id':'id-1','owner_id':'owner-1','kind':'search-demo','query':'roofers','location':'Houston','requested':2}]
    completed=[]
    failed=[]
    monkeypatch.setattr(worker.postgres,'claim_next_job',lambda: claimed.pop(0) if claimed else None)
    monkeypatch.setattr(worker.postgres,'finish_job',lambda *args: completed.append(args))
    monkeypatch.setattr(worker.postgres,'fail_job',lambda *args: failed.append(args))
    assert worker.process_one() is True
    assert len(completed)==1 and completed[0][0:2]==('owner-1','id-1')
    assert len(completed[0][2])==2
    assert failed==[]
    assert worker.process_one() is False


def test_worker_import_reads_durable_payload(monkeypatch):
    uploaded=b'Name,Phone\nExample Co,7135550101\n'
    monkeypatch.setattr(worker.postgres,'claim_next_job',lambda: {'id':'i','owner_id':'o','kind':'csv-import','csv_bytes':uploaded})
    result=[]
    monkeypatch.setattr(worker.postgres,'finish_job',lambda *args: result.append(args))
    monkeypatch.setattr(worker.postgres,'fail_job',lambda *args: None)
    assert worker.process_one() is True
    assert result[0][2][0]['name']=='Example Co'


def test_worker_handles_invalid_upload(monkeypatch):
    monkeypatch.setattr(worker.postgres,'claim_next_job',lambda: {'id':'i','owner_id':'o','kind':'csv-import','csv_bytes':b'bad'})
    failed=[]
    monkeypatch.setattr(worker.postgres,'finish_job',lambda *args: None)
    monkeypatch.setattr(worker.postgres,'fail_job',lambda *args: failed.append(args))
    assert worker.process_one() is True
    assert len(failed)==1 and 'CSV' in failed[0][2]
