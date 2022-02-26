from typing import Dict

import pytest
from fastapi import status
from headers import AUTHORIZATION

from urls import *


def do_login(client, data: Dict):
    resp = client.post(LOGIN, json=data)
    assert resp.status_code == 200, resp.json()
    header = resp.headers[AUTHORIZATION]
    alg, token = header.split()
    assert alg == "bearer"


def test_user_login_username(client, login):
    username, email, password = login
    data = {"username": username, "password": password}
    do_login(client, data)


def test_user_login_email(client, login):
    username, email, password = login
    data = {"email": email, "password": password}
    do_login(client, data)


def test_user_create(client, credentials):
    username, email, password = credentials

    resp = client.post(
        "/register", json={"username": username, "email": email, "password": password}
    )

    assert resp.status_code == 201, resp.json()


def test_user_create_and_login_unverified(client, credentials):
    test_user_create(client, credentials)
    username, email, password = credentials
    data = {"username": username, "password": password}
    resp = client.post(LOGIN, json=data)
    assert resp.status_code == 403 and "verified" in resp.json()["error"]["message"]


@pytest.mark.anyio
async def test_user_un_publish_project_and_delete(client, login, db):
    username, email, password = login
    try:
        # LOGIN
        data = {"username": username, "password": password}
        resp = client.post(LOGIN, json=data)

        # TRY UN-PUBLISH
        resp = client.delete(
            PROJECT.format(username),
            headers={AUTHORIZATION: resp.headers[AUTHORIZATION]},
        )
        assert resp.status_code in {401, 403}, resp.json()

        # PREP
        _id = await db.fetch_val(
            "INSERT INTO projects (name, published, default_language_id) VALUE (:pname, 1, 1) RETURNING id",
            values=dict(pname=username),
        )
        await db.execute(
            f"INSERT INTO project_information (name, lang_id, project_id) VALUE ('Test', 1, {_id})"
        )
        await db.execute(
            """
            INSERT INTO project_admins (project_id, user_id) 
            SELECT 
                (SELECT p.id FROM projects p WHERE p.name = :pname), 
                (SELECT u.id FROM users u WHERE u.username = :uname)
            """,
            values=dict(pname=username, uname=username),
        )

        # LOGIN
        resp = client.post("/login", json=data)

        # UN-PUBLISH
        resp = client.delete(
            PROJECT.format(username),
            headers={AUTHORIZATION: resp.headers[AUTHORIZATION]},
        )

        assert resp.status_code == status.HTTP_204_NO_CONTENT, (
                str(await db.fetch_all("SELECT name, published FROM projects"))
                + "\n"
                + resp.text
        )

        assert client.get(PROJECT.format(username)).status_code == 403

        assert (
                await db.fetch_val(
                    "SELECT published FROM projects WHERE name = :pname",
                    values=dict(pname=username),
                )
                == 0
        )

        # DELETE FULLY FROM DB
        await db.execute(
            "DELETE FROM projects WHERE name = :pname", values=dict(pname=username)
        )
    finally:
        await db.execute(
            "DELETE FROM projects WHERE name = :pname", values=dict(pname=username)
        )
