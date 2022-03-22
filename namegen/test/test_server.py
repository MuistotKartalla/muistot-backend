import re

from app.main import app
from fastapi.testclient import TestClient


def test_get():
    names = set()
    with TestClient(app) as client:
        for _ in range(0, 1000):
            r = client.get('/')
            assert r.status_code == 200
            assert 'value' in r.json()
            assert re.match(r'^.+#\d{4}$', r.json()['value'])
            names.add(r.json()['value'])
    assert len(names) == 1000
