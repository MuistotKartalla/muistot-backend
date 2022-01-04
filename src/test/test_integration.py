from fastapi.testclient import TestClient


def test_hello(client: TestClient):
    resp = client.get("/")
    assert resp.json() == {"hello": "world"}
