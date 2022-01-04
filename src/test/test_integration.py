from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)


def test_hello():
    resp = client.get("/")
    assert resp.json() == {"hello": "world", "a": 0}
