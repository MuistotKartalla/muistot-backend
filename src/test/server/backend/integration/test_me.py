from secrets import token_urlsafe as gen_pw

import pytest
from fastapi import status

from utils import authenticate


@pytest.fixture
def user(users):
    yield users[0]


@pytest.fixture(autouse=True)
async def backup(db, anyio_backend, user):
    pre = await db.fetch_one(
        "SELECT id, username, email, password_hash FROM users WHERE username = :user",
        values=dict(user=user.username)
    )
    yield
    print(type(pre))
    print(dir(pre))
    await db.execute(
        "UPDATE users SET username=:username, email=:email, password_hash=:password_hash WHERE id=:id",
        values=pre
    )


def test_change_username(client, auth, user):
    from passlib.pwd import genword
    new_username = genword(length=30)
    # Change
    r = client.post(f"/me/username?username={new_username}", headers=auth)
    assert r.status_code == status.HTTP_204_NO_CONTENT
    # Logged Out
    r = client.get("/me", headers=auth)
    assert r.status_code == status.HTTP_401_UNAUTHORIZED
    # Re-Auth
    auth = authenticate(client, new_username, user.password)
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


def test_change_password(client, auth, user):
    username, email, pw = user
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


def test_logout_single_session(client, user):
    username = user.username
    auth_header1 = authenticate(client, user.username, user.password)
    auth_header2 = authenticate(client, user.username, user.password)

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


def test_logout_all_sessions(client, user):
    username = user.username
    auth_header1 = authenticate(client, user.username, user.password)
    auth_header2 = authenticate(client, user.username, user.password)

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


def test_change_to_same_username(client, auth, user):
    r = client.post("/me/username", params=dict(username=user.username), headers=auth)
    assert r.status_code == 304


def test_change_to_same_email(client, auth, user):
    r = client.post("/me/email", params=dict(email=user.email), headers=auth)
    assert r.status_code == 304


def test_patch_country(client, auth):
    r = client.patch("/me", json=dict(country="fi"), headers=auth)
    assert r.status_code == 204
    r = client.patch("/me", json=dict(country="fi"), headers=auth)
    assert r.status_code == 204
