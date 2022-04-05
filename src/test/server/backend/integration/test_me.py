from secrets import token_urlsafe as gen_pw

import pytest
from fastapi import status

from utils import authenticate


@pytest.fixture(autouse=True)
async def backup(db, anyio_backend, username):
    pre = await db.fetch_one("SELECT id, username, email, password_hash FROM users")
    yield
    await db.execute(
        "UPDATE users SET username=:username, email=:email, password_hash=:password_hash WHERE id=:id",
        values=dict(**pre)
    )


def test_change_username(client, auth, login):
    from passlib.pwd import genword
    w = genword(length=30)
    # Change
    r = client.post(f"/me/username?username={w}", headers=auth)
    assert r.status_code == status.HTTP_204_NO_CONTENT
    # Logged Out
    r = client.get("/me", headers=auth)
    assert r.status_code == status.HTTP_401_UNAUTHORIZED
    # Re-Auth
    auth = authenticate(client, w, login[2])
    r = client.get("/me", headers=auth)
    assert r.status_code == status.HTTP_200_OK


def test_change_email(client, auth):
    w = gen_pw(30)
    # Change
    r = client.post(f"/me/email?email={w}@example.com", headers=auth)
    assert r.status_code == status.HTTP_204_NO_CONTENT
    # Not Logged Out
    r = client.get("/me", headers=auth)
    assert r.status_code == status.HTTP_200_OK


def test_change_password(client, auth, username):
    w = gen_pw(30)
    # Change
    r = client.put(f"/me/password?password={w}", headers=auth)
    assert r.status_code == status.HTTP_200_OK
    # Logged Out
    r = client.get("/me", headers=auth)
    assert r.status_code == status.HTTP_401_UNAUTHORIZED
    # Re-Auth
    auth = authenticate(client, username, w)
    r = client.get("/me", headers=auth)
    assert r.status_code == status.HTTP_200_OK


def test_logout_single_session(client, users):
    username = users[0].username
    auth_header1 = authenticate(client, users[0].username, users[0].password)
    auth_header2 = authenticate(client, users[0].username, users[0].password)

    r = client.get("/me", headers=auth_header1)
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["username"] == username
    r = client.get("/me", headers=auth_header2)
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["username"] == username

    r = client.delete("/me", headers=auth_header1)
    assert r.status_code == status.HTTP_204_NO_CONTENT

    r = client.get("/me", headers=auth_header1)
    assert r.status_code == status.HTTP_401_UNAUTHORIZED
    r = client.get("/me", headers=auth_header2)
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["username"] == username


def test_logout_all_sessions(client, users):
    username = users[0].username
    auth_header1 = authenticate(client, users[0].username, users[0].password)
    auth_header2 = authenticate(client, users[0].username, users[0].password)

    r = client.get("/me", headers=auth_header1)
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["username"] == username
    r = client.get("/me", headers=auth_header2)
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["username"] == username

    r = client.delete("/me/sessions", headers=auth_header1)
    assert r.status_code == status.HTTP_204_NO_CONTENT

    r = client.get("/me", headers=auth_header1)
    assert r.status_code == status.HTTP_401_UNAUTHORIZED
    r = client.get("/me", headers=auth_header2)
    assert r.status_code == status.HTTP_401_UNAUTHORIZED


def test_change_to_same_username(client, auth, users):
    user = users[0]
    r = client.post("/me/username", params=dict(username=user.username), headers=auth)
    assert r.status_code == 304


def test_change_to_same_email(client, auth, users):
    user = users[0]
    r = client.post("/me/email", params=dict(email=user.email), headers=auth)
    assert r.status_code == 304


def test_patch_country(client, auth):
    r = client.patch("/me", json=dict(country="fi"), headers=auth)
    assert r.status_code == 204
    r = client.patch("/me", json=dict(country="fi"), headers=auth)
    assert r.status_code == 204
