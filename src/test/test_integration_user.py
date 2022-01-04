from typing import Dict

import pytest
from databases import Database
from fastapi.testclient import TestClient


@pytest.fixture(name="credentials")
def _credentials():
    """username, email, password"""
    from passlib.pwd import genword
    length = 64
    username, email, password = genword(length=length), genword(length=length), genword(length=length)
    yield username, email, password


@pytest.fixture(name="login")
async def create_user(db: Database, credentials):
    from app.logins._default import hash_password
    username, email, password = credentials
    await db.execute(
        "INSERT INTO users (email, username, password_hash, verified) VALUE (:email, :username, :password, 1)",
        values=dict(password=hash_password(password), username=username, email=email)
    )
    yield username, email, password


@pytest.fixture(autouse=True)
async def delete_user(db: Database, credentials):
    yield
    username = credentials[0]
    await db.execute("DELETE FROM users WHERE username = :un", values=dict(un=username))
    assert await db.fetch_val("SELECT EXISTS(SELECT * FROM users WHERE username = :un)", values=dict(un=username)) == 0


def do_login(client: TestClient, data: Dict, username: str):
    from app.headers import AUTHORIZATION
    from app.security.jwt import read_jwt
    resp = client.post("/login", json=data)

    assert resp.status_code == 200, resp.json()
    header = resp.headers[AUTHORIZATION]
    alg, token = header.split()
    assert alg == 'JWT'
    assert read_jwt(token)['sub'] == username


@pytest.mark.anyio
async def test_user_login_username(client: TestClient, login):
    username, email, password = login
    data = {
        'username': username,
        'password': password
    }
    do_login(client, data, username)


@pytest.mark.anyio
async def test_user_login_email(client: TestClient, login):
    username, email, password = login
    data = {
        'email': email,
        'password': password
    }
    do_login(client, data, username)


@pytest.mark.anyio
async def test_user_create(client: TestClient, credentials):
    username, email, password = credentials

    resp = client.post("/register", json={
        'username': username,
        'email': email,
        'password': password
    })

    assert resp.status_code == 201, resp.json()


@pytest.mark.anyio
async def test_user_create_and_login_unverified(client: TestClient, credentials):
    await test_user_create(client, credentials)
    username, email, password = credentials
    data = {
        'username': username,
        'password': password
    }
    resp = client.post("/login", json=data)
    assert resp.status_code == 401 and 'verified' in resp.json()["error"]["message"]
