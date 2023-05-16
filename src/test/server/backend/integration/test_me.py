from secrets import token_urlsafe as gen_pw

import pytest
from fastapi import status
from headers import AUTHORIZATION


@pytest.fixture(autouse=True)
async def backup(db, login):
    pre = await db.fetch_one(
        "SELECT id, username, email FROM users WHERE username = :login",
        values=dict(login=login.username)
    )
    yield
    await db.execute(
        "UPDATE users SET username=:username, email=:email WHERE id=:id",
        values=dict(username=pre["username"], email=pre["email"], id=pre["id"])
    )


@pytest.mark.anyio
async def test_change_username(client, auth, login):
    from passlib.pwd import genword
    new_username = genword(length=30)
    # Change
    r = await client.post(f"/me/username?username={new_username}", headers=auth)
    assert r.status_code == status.HTTP_200_OK
    assert AUTHORIZATION in r.headers
    auth_new = r.headers[AUTHORIZATION]
    # Logged Out
    r = await client.get("/me", headers=auth)
    assert r.status_code == status.HTTP_401_UNAUTHORIZED
    # Returned session is valid
    r = await client.get("/me", headers={AUTHORIZATION: auth_new})
    assert r.status_code == status.HTTP_200_OK


@pytest.mark.anyio
async def test_change_email(client, auth):
    w = gen_pw(30)
    # Change
    r = await client.post(f"/me/email?email={w}@example.com", headers=auth)
    assert r.status_code == status.HTTP_200_OK
    assert AUTHORIZATION in r.headers
    auth_new = r.headers[AUTHORIZATION]
    # Logged Out
    r = await client.get("/me", headers=auth)
    assert r.status_code == status.HTTP_401_UNAUTHORIZED
    # Returned token is valid
    r = await client.get("/me", headers={AUTHORIZATION: auth_new})
    assert r.status_code == status.HTTP_200_OK


@pytest.mark.anyio
async def test_logout_single_session(client, login, authenticate):
    username = login.username
    auth_header1 = await authenticate(login)
    auth_header2 = await authenticate(login)

    r = await client.get("/me", headers=auth_header1)
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["username"] == username
    r = await client.get("/me", headers=auth_header2)
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["username"] == username

    r = await client.delete("/me", headers=auth_header1)
    assert r.status_code == status.HTTP_204_NO_CONTENT

    r = await client.get("/me", headers=auth_header1)
    assert r.status_code == status.HTTP_401_UNAUTHORIZED
    r = await client.get("/me", headers=auth_header2)
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["username"] == username


@pytest.mark.anyio
async def test_logout_all_sessions(client, login, authenticate):
    username = login.username
    auth_header1 = await authenticate(login)
    auth_header2 = await authenticate(login)

    r = await client.get("/me", headers=auth_header1)
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["username"] == username
    r = await client.get("/me", headers=auth_header2)
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["username"] == username

    r = await client.delete("/me/sessions", headers=auth_header1)
    assert r.status_code == status.HTTP_204_NO_CONTENT

    r = await client.get("/me", headers=auth_header1)
    assert r.status_code == status.HTTP_401_UNAUTHORIZED
    r = await client.get("/me", headers=auth_header2)
    assert r.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.anyio
async def test_change_to_same_username(client, auth, login):
    r = await client.post("/me/username", params=dict(username=login.username), headers=auth)
    assert r.status_code == 304


@pytest.mark.anyio
async def test_change_to_same_email(client, auth, login):
    r = await client.post("/me/email", params=dict(email=login.email), headers=auth)
    assert r.status_code == 304


@pytest.mark.anyio
async def test_patch_country(client, auth):
    import pycountry

    r = await client.patch("/me", json=dict(country="fi"), headers=auth)
    assert r.status_code == 204
    r = await client.get("/me", headers=auth)
    assert r.status_code == 200
    assert r.json()["country"] == pycountry.countries.get(alpha_2="fi").alpha_3


@pytest.mark.anyio
async def test_patch_me_multiple_times(client, auth):
    r = await client.get("/me", headers=auth)
    assert r.status_code == 200
    assert r.json().get("first_name", None) is None

    r = await client.patch("/me", json=dict(first_name="test1", last_name="test_no_show"), headers=auth)
    assert r.status_code == 204

    r = await client.patch("/me", json=dict(last_name="test2"), headers=auth)
    assert r.status_code == 204

    r = await client.get("/me", headers=auth)
    assert r.status_code == 200

    m = r.json()
    assert m["first_name"] == "test1"
    assert m["last_name"] == "test2"
