from typing import Dict

import pytest
from fastapi import status
from muistoja.errors import Error

from utils import *


def do_login(client, data: Dict):
    r = client.post(LOGIN, json=data)
    check_code(status.HTTP_200_OK, r)
    assert r.headers[AUTHORIZATION].startswith("bearer")


def test_user_login_username(client, login):
    username, email, password = login
    data = {"username": username, "password": password}
    do_login(client, data)


def test_user_login_email(client, login):
    username, email, password = login
    data = {"email": email, "password": password}
    do_login(client, data)


def test_user_login_both(client, login):
    username, email, password = login
    data = {"email": email, "username": username, "password": password}
    r = client.post(LOGIN, json=data)
    check_code(status.HTTP_422_UNPROCESSABLE_ENTITY, r)


@pytest.mark.anyio
async def test_user_create(client, db, login):
    username, email, password = login
    await db.execute("DELETE FROM users WHERE username = :u", values=dict(u=username))

    r = client.post(REGISTER, json={"username": username, "email": email, "password": password})
    check_code(status.HTTP_201_CREATED, r)


@pytest.mark.anyio
async def test_user_create_and_login_unverified(client, db, login):
    username, email, password = login
    await db.execute("UPDATE users SET verified = 0 WHERE username = :u", values=dict(u=username))

    data = {"username": username, "password": password}
    r = client.post(LOGIN, json=data)
    check_code(status.HTTP_403_FORBIDDEN, r)
    assert "verified" in to(Error, r).error.message
