from typing import Dict

import pytest
from fastapi.testclient import TestClient

from urls import *


def do_login(client: TestClient, data: Dict, username: str):
    from app.headers import AUTHORIZATION
    from app.security.jwt import read_jwt
    from app.security.scopes import SUBJECT
    resp = client.post(LOGIN, json=data)

    assert resp.status_code == 200, resp.json()
    header = resp.headers[AUTHORIZATION]
    alg, token = header.split()
    assert alg == 'bearer'
    assert read_jwt(token)[SUBJECT] == username


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
    resp = client.post(LOGIN, json=data)
    assert resp.status_code == 403 and 'verified' in resp.json()["error"]["message"]


@pytest.mark.anyio
async def test_user_un_publish_project_and_de_admin_on_delete(client: TestClient, login, db):
    from app.headers import AUTHORIZATION
    from app.security.auth import get_user, HTTPBearer
    from fastapi import status

    username, email, password = login
    try:
        # LOGIN
        data = {'username': username, 'password': password}
        resp = client.post(LOGIN, json=data)

        # TRY UN-PUBLISH
        resp = client.delete(PROJECT.format(username), headers={AUTHORIZATION: resp.headers[AUTHORIZATION]})
        assert resp.status_code in {401, 403}, resp.json()

        # PREP
        await db.execute(
            "INSERT INTO projects (name, published, default_language_id) VALUE (:pname, 1, 1)",
            values=dict(pname=username)
        )
        await db.execute(
            """
            INSERT INTO project_admins (project_id, user_id) 
            SELECT 
                (SELECT p.id FROM projects p WHERE p.name = :pname), 
                (SELECT u.id FROM users u WHERE u.username = :uname)
            """,
            values=dict(pname=username, uname=username)
        )

        # LOGIN
        resp = client.post("/login", json=data)

        # UN-PUBLISH
        resp = client.delete(
            PROJECT.format(username),
            headers={AUTHORIZATION: resp.headers[AUTHORIZATION]}
        )
        print(client.get(PROJECT.format(username)).json())
        assert resp.status_code == status.HTTP_204_NO_CONTENT, await db.fetch_all(
            "SELECT name, published FROM projects"
        )
        assert await db.fetch_val(
            "SELECT published FROM projects WHERE name = :pname",
            values=dict(pname=username)
        ) == 0

        # DELETE FULLY FROM DB
        await db.execute(
            "DELETE FROM projects WHERE name = :pname",
            values=dict(pname=username)
        )

        # RE-LOGIN
        resp = client.post(LOGIN, json=data)

        o = type('', (), {})()
        o.state = type('', (), {})()
        o.state.resolved = False

        user = get_user(o, await HTTPBearer()(resp))

        # ASSERT LOST ADMIN
        assert user.is_authenticated
        assert not user.is_admin_in(username)
    finally:
        await db.execute("DELETE FROM projects WHERE name = :pname", values=dict(pname=username))
