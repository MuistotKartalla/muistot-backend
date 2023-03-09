from urllib.parse import urlencode

import pytest
from fastapi import status
from headers import AUTHORIZATION
from muistot.login.logic.models import LoginQuery
from pydantic import ValidationError

from login_urls import STATUS, REGISTER, CONFIRM, PW_LOGIN


@pytest.fixture
async def admin(db, user):
    name = "'test_aaaaaa'"
    _id = await db.fetch_val(f"INSERT INTO projects (name, default_language_id) VALUE ({name}, 1) RETURNING id")
    await db.execute(f"INSERT INTO project_admins (project_id, user_id) VALUE ({_id}, {user.id})")
    yield
    await db.execute(f"DELETE FROM projects WHERE name = {name}")


@pytest.fixture
async def superuser(db, user):
    await db.execute(f"INSERT INTO superusers (user_id) VALUE ({user.id})")
    yield
    await db.execute(f"DELETE FROM superusers WHERE user_id = {user.id}")


@pytest.mark.anyio
async def test_query_model():
    with pytest.raises(ValidationError) as e:
        LoginQuery(username=None, email=None, password="aaaaa")
    assert "Identifier Required" in str(e.value)

    with pytest.raises(ValidationError) as e:
        LoginQuery(username="aaaaaaaa", email="a@example.com", password="aaaaa")
    assert "Only one" in str(e.value)

    with pytest.raises(ValidationError) as e:
        LoginQuery(password=None)
    assert "Only one" not in str(e.value) and "Identifier Required" not in str(e.value)

    # No Throws
    LoginQuery(username="aaaaa", password="aaaaa")
    LoginQuery(email="aaaaa@example.com", password="aaaaa")


@pytest.mark.anyio
async def test_status_not_logged_in(client):
    r = await client.get(STATUS)
    assert r.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.anyio
async def test_register_double_not_allowed(client, non_existent_email):
    req = lambda: client.post(REGISTER, json={
        "email": non_existent_email,
        "username": "test_does_not_exists#1323",
        "password": "testtesttest@@@@11421321"
    })
    r = await req()
    assert r.status_code == status.HTTP_201_CREATED
    r = await req()
    assert r.status_code == status.HTTP_409_CONFLICT


@pytest.mark.anyio
async def test_register_confirm(client, non_existent_email, capture_mail):
    r = await client.post(REGISTER, json={
        "email": non_existent_email,
        "username": "test_does_not_exists#1323",
        "password": "testtesttest@@@@11421321"
    })
    assert r.status_code == status.HTTP_201_CREATED

    # Check email and verify
    token = capture_mail[("register", non_existent_email)]["token"]
    user = capture_mail[("register", non_existent_email)]["user"]
    r = await client.post(f"{CONFIRM}?{urlencode(dict(user=user, token=token))}")
    assert r.status_code == status.HTTP_200_OK
    assert r.headers[AUTHORIZATION] is not None

    # Check status
    auth = r.headers[AUTHORIZATION]
    r = await client.get(STATUS, headers={AUTHORIZATION: auth})
    assert r.status_code == status.HTTP_200_OK


@pytest.mark.anyio
async def test_login_username(client, verified_user):
    user = verified_user
    r = await client.post(PW_LOGIN, json={"username": user.username, "password": user.password})
    assert r.status_code == status.HTTP_200_OK, r.text

    # Check status
    auth = r.headers[AUTHORIZATION]
    r = await client.get(STATUS, headers={AUTHORIZATION: auth})
    assert r.status_code == status.HTTP_200_OK


@pytest.mark.anyio
async def test_login_email(client, verified_user):
    user = verified_user
    r = await client.post(PW_LOGIN, json={"email": user.email, "password": user.password})
    assert r.status_code == status.HTTP_200_OK, r.text

    # Check status
    auth = r.headers[AUTHORIZATION]
    r = await client.get(STATUS, headers={AUTHORIZATION: auth})
    assert r.status_code == status.HTTP_200_OK


@pytest.mark.anyio
async def test_login_both_fails(client, verified_user):
    user = verified_user
    r = await client.post(PW_LOGIN, json={
        "email": user.email,
        "username": user.username,
        "password": user.password
    })
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.anyio
async def test_no_register_with_header(client, verified_user):
    user = verified_user
    r = await client.post(PW_LOGIN, json={"email": user.email, "password": user.password})
    assert r.status_code == status.HTTP_200_OK, r.text
    auth = r.headers[AUTHORIZATION]
    r = await client.post(REGISTER, headers={AUTHORIZATION: auth}, json={
        "email": "a@example.com",
        "username": "aaaaaaaaa",
        "password": "aaaaaaaaa"
    })
    assert r.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.anyio
async def test_login_scopes_admin_works(client, verified_user, admin):
    from muistot.security import scopes

    user = verified_user
    r = await client.post(PW_LOGIN, json={"email": user.email, "password": user.password})
    assert r.status_code == status.HTTP_200_OK, r.text
    auth = r.headers[AUTHORIZATION]

    s = client.app.state.SessionManager.get_session(auth.partition(' ')[2])
    assert scopes.ADMIN in s.data["scopes"]
    assert len(s.data["projects"]) == 1

    # Check status
    r = await client.get(STATUS, headers={AUTHORIZATION: auth})
    assert r.status_code == status.HTTP_200_OK


@pytest.mark.anyio
async def test_login_scopes_superuser_works(client, verified_user, superuser):
    from muistot.security import scopes

    user = verified_user
    r = await client.post(PW_LOGIN, json={"username": user.username, "password": user.password})
    assert r.status_code == status.HTTP_200_OK, r.text
    auth = r.headers[AUTHORIZATION]

    s = client.app.state.SessionManager.get_session(auth.partition(' ')[2])
    assert scopes.SUPERUSER in s.data["scopes"]
    assert scopes.ADMIN in s.data["scopes"]

    # Check status
    r = await client.get(STATUS, headers={AUTHORIZATION: auth})
    assert r.status_code == status.HTTP_200_OK


@pytest.mark.anyio
async def test_verify_token_not_exists(client, user, capture_mail):
    r = await client.post(f"{CONFIRM}?{urlencode(dict(user=user.username, token='ööööööääääää'))}")
    assert r.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.anyio
async def test_login_unverified_not_allowed(client, user):
    r = await client.post(PW_LOGIN, json={"email": user.email, "password": user.password})
    assert r.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.anyio
async def test_login_not_exists_not_allowed(client, user):
    r = await client.post(PW_LOGIN, json={"email": "aaaa" + user.email, "password": user.password})
    assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.anyio
async def test_login_bad_password_not_allowed(client, user):
    r = await client.post(PW_LOGIN, json={"email": user.email, "password": "aaa" + user.password})
    assert r.status_code == status.HTTP_400_BAD_REQUEST
