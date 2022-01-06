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
    from app.security.scopes import SUBJECT
    resp = client.post("/login", json=data)

    assert resp.status_code == 200, resp.json()
    header = resp.headers[AUTHORIZATION]
    alg, token = header.split()
    assert alg == 'JWT'
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
    resp = client.post("/login", json=data)
    assert resp.status_code == 401 and 'verified' in resp.json()["error"]["message"]


@pytest.mark.anyio
async def test_user_un_publish_project_and_de_admin_on_delete(client: TestClient, login, db):
    from app.headers import AUTHORIZATION
    from app.security.jwt import read_jwt
    from app.security.auth import CustomUser
    from fastapi import status

    username, email, password = login
    try:
        # LOGIN
        data = {'username': username, 'password': password}
        resp = client.post("/login", json=data)

        # TRY UN-PUBLISH
        resp = client.delete(f'/api/projects/{username}', headers={AUTHORIZATION: resp.headers[AUTHORIZATION]})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED, resp.json()

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
            f'/api/projects/{username}',
            headers={AUTHORIZATION: resp.headers[AUTHORIZATION]}
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT, resp.json()
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
        resp = client.post("/login", json=data)
        user = CustomUser(read_jwt(resp.headers[AUTHORIZATION].split()[1]))

        # ASSERT LOST ADMIN
        assert user.is_authenticated
        assert not user.is_admin_in(username)
    finally:
        await db.execute("DELETE FROM projects WHERE name = :pname", values=dict(pname=username))
