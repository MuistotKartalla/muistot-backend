import re

import pytest
from fastapi.testclient import TestClient

from namegen import app


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def test_get(client):
    names = set()
    for _ in range(0, 100):
        r = client.get('/')
        assert r.status_code == 200
        assert 'value' in r.json()
        assert re.match(r'^.+#\d{4}$', r.json()['value'])
        names.add(r.json()['value'])
    assert len(names) == 100


def test_get_disabled(client):
    client.post('/disable')
    assert client.get('/').status_code == 500


def test_get_disabled_release(client):
    test_get_disabled(client)
    client.post('/disable')
    assert client.get('/').status_code == 200


def test_get_locked(client):
    client.post('/lock?username=a')
    assert client.get('/').json()['value'] == 'a'
    assert client.get('/').json()['value'] == 'a'


def test_get_locked_release(client):
    test_get_locked(client)

    client.post('/lock')
    assert client.get('/').json()['value'] != 'abcd'
    assert client.get('/').json()['value'] != 'abcd'
