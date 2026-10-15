from app import storage
from conftest import USER_A


def test_postgres_mode_queues_without_in_process_execution(client, headers, monkeypatch):
    from app import main
    queued=[]
    monkeypatch.setattr(storage,'is_postgres',lambda: True)
    monkeypatch.setattr(storage,'create_job',lambda owner,kind,query,location,requested,**kw: queued.append((owner,kind,kw)) or {'id':'new-job','status':'queued'})
    monkeypatch.setattr(main,'run_demo_job',lambda *args: (_ for _ in ()).throw(AssertionError('Should not run inline')))
    response=client.post('/api/jobs/search',json={'query':'roofers','location':'Houston','max_results':2}, headers=headers(USER_A))
    assert response.status_code==202
    assert response.json()['status']=='queued'
    assert queued[0][0]==USER_A


def test_postgres_import_upload_payload_is_sent_to_db(client, headers, monkeypatch):
    from app import main
    uploads=[]
    monkeypatch.setattr(storage,'is_postgres',lambda: True)
    monkeypatch.setattr(storage,'create_job',lambda owner,kind,query,location,requested,**kw: uploads.append((owner,kind,kw.get('csv_bytes'))) or {'id':'import','status':'queued'})
    monkeypatch.setattr(main,'run_import_job',lambda *args: (_ for _ in ()).throw(AssertionError('Should not run inline')))
    result=client.post('/api/jobs/import',headers=headers(USER_A),files={'file':('leads.csv',b'Name,Phone\nTest,7135550101','text/csv')})
    assert result.status_code==202
    assert uploads[0][0]==USER_A and uploads[0][1]=='csv-import'
    assert uploads[0][2].startswith(b'Name')


def test_prod_limits_return_429(client, headers, monkeypatch):
    monkeypatch.setattr(storage,'is_postgres',lambda: True)
    def limit(*a, **kw):
        raise ValueError('Job limit reached')
    monkeypatch.setattr(storage,'create_job',limit)
    result=client.post('/api/jobs/search',json={'query':'roofers','location':'Houston'},headers=headers(USER_A))
    assert result.status_code==429
