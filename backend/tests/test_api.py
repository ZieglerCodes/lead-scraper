import io
from app import db
from conftest import USER_A, USER_B, make_token


def test_health_is_public_but_private_routes_require_token(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['phase'] == 4
    for path in ['/api/me', '/api/jobs', '/api/jobs/any', '/api/jobs/any/leads']:
        assert client.get(path).status_code == 401
    assert client.post('/api/jobs/search', json={'query':'roofers','location':'Houston'}).status_code == 401
    assert client.post('/api/jobs/import', files={'file':('contacts.csv', b'Name,Phone\nExample,7135550101','text/csv')}).status_code == 401


def test_search_owner_scoping_and_leads(client, headers):
    a = headers(USER_A)
    b = headers(USER_B)
    assert client.get('/api/me', headers=a).json() == {'id': USER_A}
    resp = client.post('/api/jobs/search', json={'query':'roofers', 'location':'Houston', 'max_results':3}, headers=a)
    assert resp.status_code == 202
    job_id = resp.json()['id']
    job = client.get(f'/api/jobs/{job_id}', headers=a).json()
    assert job['status'] == 'completed'
    assert job['found'] == 3
    assert job['owner_id'] == USER_A
    assert len(client.get(f'/api/jobs/{job_id}/leads', headers=a).json()['leads']) == 3
    assert len(client.get('/api/jobs', headers=a).json()['jobs']) == 1
    assert client.get('/api/jobs', headers=b).json()['jobs'] == []
    assert client.get(f'/api/jobs/{job_id}', headers=b).status_code == 404
    assert client.get(f'/api/jobs/{job_id}/leads', headers=b).status_code == 404
    assert client.get(f'/api/jobs/{job_id}', headers={**b, 'X-User-Id': USER_A}).status_code == 404
    assert db.get_leads(USER_B, job_id) == []


def test_import_owner_scoping(client, headers):
    data = b'Name,Phone,Website\nAcme Roofing,7135550101,https://example.com\nOther Roofing,7135550199,https://example.org\n'
    resp = client.post('/api/jobs/import', headers=headers(USER_B), files={'file':('contacts.csv', data, 'text/csv')})
    assert resp.status_code == 202, resp.text
    job = client.get(f"/api/jobs/{resp.json()['id']}", headers=headers(USER_B)).json()
    assert job['status'] == 'completed'
    assert job['found'] == 2
    assert client.get('/api/jobs', headers=headers(USER_A)).json()['jobs'] == []
    assert client.get(f"/api/jobs/{job['id']}/leads", headers=headers(USER_A)).status_code == 404


def test_reject_bad_tokens(client, headers, token):
    malformed = 'Bearer rubbish'
    assert client.get('/api/jobs', headers={'Authorization':malformed}).status_code == 401
    cases = [
        token(audience='other'),
        token(issuer='https://evil.example/auth/v1'),
        token(role='service_role'),
        token(session=False),
        token(expires=-3600),
        token(key=__import__('cryptography').hazmat.primitives.asymmetric.rsa.generate_private_key(public_exponent=65537,key_size=2048)),
    ]
    for jwt_token in cases:
        assert client.get('/api/jobs', headers={'Authorization':f'Bearer {jwt_token}'}).status_code == 401


def test_input_validation(client, headers):
    auth = headers(USER_A)
    assert client.post('/api/jobs/search', json={'query':'x', 'location':'Houston'}, headers=auth).status_code == 422
    assert client.post('/api/jobs/search', json={'query':'roofers', 'location':'Houston', 'source':'google'}, headers=auth).status_code == 422
    assert client.post('/api/jobs/import', headers=auth, files={'file':('x.txt', b'hello')}).status_code == 415
    assert client.post('/api/jobs/import', headers=auth, files={'file':('x.csv', b'')}).status_code == 400
    assert client.post('/api/jobs/import', headers=auth, files={'file':('x.csv', b'x' * (2*1024*1024 + 1))}).status_code == 413


def test_owner_checked_in_internal_mutations(client, headers):
    job = db.create_job(USER_A, 'search-demo', 'roofers', 'Houston', 2)
    db.set_job(USER_B, job['id'], 'completed', found=10)
    assert db.get_job(USER_A, job['id'])['status'] == 'queued'
    try:
        db.insert_leads(USER_B, job['id'], [{'name':'Injected','address':None,'phone':None,'email':None,'website':None,'source':'synthetic-demo'}])
        assert False, 'Must reject insert into someone elses job'
    except ValueError:
        pass
