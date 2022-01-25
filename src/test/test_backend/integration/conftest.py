from typing import cast

import databases
import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from muistoja.backend import main
from muistoja.core.database.connections import make_url_from_database_config
from muistoja.core.security.auth import User
from muistoja.core.security.password import hash_password
from muistoja.core.security.scopes import SECURITY_SCOPES
from passlib.pwd import genword
from pymysql.err import OperationalError

from utils import authenticate as auth


@pytest.fixture
async def db():
    db_instance = databases.Database(make_url_from_database_config("default"), force_rollback=False)
    while True:
        try:
            await db_instance.connect()
            break
        except OperationalError:
            pass
    try:
        yield db_instance
    finally:
        await db_instance.disconnect()


@pytest.fixture
def client(db):
    with TestClient(main.app) as instance:
        yield instance


@pytest.fixture(name="credentials")
def _credentials():
    """username, email, password"""
    length = 10
    username, email, password = genword(length=length), genword(length=length), genword(length=length)
    yield username, email, password


@pytest.fixture(autouse=True)
async def delete_user(db: databases.Database, credentials):
    username, email, password = credentials
    yield
    await db.execute("DELETE FROM users WHERE username = :un", values=dict(un=username))
    assert await db.fetch_val("SELECT EXISTS(SELECT * FROM users WHERE username = :un)", values=dict(un=username)) == 0


@pytest.fixture(name="login")
async def create_user(db: databases.Database, credentials):
    username, email, password = credentials
    await db.execute(
        "INSERT INTO users (email, username, password_hash, verified) "
        "VALUE (:email, :username, :password, 1) ",
        values=dict(password=hash_password(password=password), username=username, email=email)
    )
    yield username, email, password


@pytest.fixture(name='superuser')
async def super_user(login):
    await db.execute(
        "INSERT INTO superusers (user_id) SELECT id FROM users WHERE username=:user",
        values=dict(user=login[0])
    )


@pytest.fixture
def mock_request(login):
    uid = login[0]

    class MockRequest:
        method = "GET"
        headers = dict()
        user = User(username=uid, scopes=set(SECURITY_SCOPES))

    return cast(Request, MockRequest())


@pytest.fixture(name='auth')
def auth_fixture(client, login):
    return auth(client, login)
