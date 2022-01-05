from fastapi.testclient import TestClient


def test_add_site_unauthenticated(client: TestClient):
    resp = client.post('/old/sites')
    assert resp.status_code == 401 and resp.json()["error"]["message"].lower() == 'unauthorized'
