import databases
import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture
async def db():
    db_instance = databases.Database("mysql://root:test@localhost:5601/muistot", force_rollback=False)
    await db_instance.connect()
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
    from passlib.pwd import genword
    length = 64
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
    from app.logins._default import hash_password
    username, email, password = credentials
    await db.execute(
        "INSERT INTO users (email, username, password_hash, verified) VALUE (:email, :username, :password, 1)",
        values=dict(password=hash_password(password), username=username, email=email)
    )
    yield username, email, password
