def test_hello(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_projects(client):
    resp = client.get("/projects")
    assert resp.status_code == 200


def test_lang(client):
    resp = client.get("/languages?q=fi")
    assert resp.json() == {"id": "fin", "name": "Finnish"}
