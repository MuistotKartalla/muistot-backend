from fastapi.testclient import TestClient


def test_hello(client: TestClient):
    resp = client.get("/api/")
    assert resp.json() == {"hello": "world"}


def test_projects(client: TestClient):
    resp = client.get("/api/projects")
    assert resp.status_code == 200
