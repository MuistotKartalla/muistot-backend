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
    from passlib.pwd import genword
    w = genword(length=30)
    # Change
    r = client.post(f"/me/email?email={w}@example.com", headers=auth)
    assert r.status_code == status.HTTP_204_NO_CONTENT
    # Not Logged Out
    r = client.get("/me", headers=auth)
    assert r.status_code == status.HTTP_200_OK


def test_change_password(client, auth, username):
    from passlib.pwd import genword
    w = genword(length=30)
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
