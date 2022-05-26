from collections import namedtuple

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from muistot import mailer
from muistot.cache import register_redis_cache
from muistot.database import Databases
from muistot.login import register_login
from muistot.mailer import Mailer, Result
from muistot.sessions import register_session_manager

User = namedtuple("User", ["username", "email"])


@pytest.fixture
def mail():
    class Mock(Mailer):

        def __init__(self):
            self.sends = list()
            self.verifys = list()

        async def send_email(self, email: str, email_type: str, **data) -> Result:
            self.sends.append((email, data))
            return Result(success=True)

    i = Mock()
    old = mailer.instance
    mailer.instance = i
    yield i
    mailer.instance = old


@pytest.fixture
def capture_mail():
    from muistot import mailer
    captured_data = dict()

    class Capturer(mailer.Mailer):

        async def send_email(self, email: str, email_type: str, **data) -> mailer.Result:
            captured_data[(email_type, email)] = dict(**data)
            return mailer.Result(success=True)

    old = mailer.instance
    mailer.instance = Capturer()
    yield captured_data
    mailer.instance = old


@pytest.fixture(scope="function")
def client(db_instance):
    app = FastAPI()

    async def mock_dep():
        async with db_instance() as c:
            yield c

    app.dependency_overrides[Databases.default] = mock_dep
    register_login(app)
    register_redis_cache(app)
    register_session_manager(app)

    app.state.FastStorage.connect()
    app.state.SessionManager.connect()

    app.state.FastStorage.redis.flushdb()
    app.state.SessionManager.redis.flushdb()

    yield TestClient(app)

    app.state.FastStorage.redis.flushdb()
    app.state.SessionManager.redis.flushdb()

    app.state.FastStorage.disconnect()
    app.state.SessionManager.disconnect()


@pytest.fixture
async def non_existent_email(db, client):
    email = "does_not_Exist_in_tests@example.com"
    yield email
    await db.execute("DELETE FROM users WHERE email = :email", values=dict(email=email))


@pytest.fixture
async def user(db, client):
    from muistot.security.password import hash_password
    from collections import namedtuple
    email = "login_test_123213123213u21389213u21321@example.com"
    username = "test_login_user#9013"
    password = "test_user"
    pwd_hash = hash_password(password=password)
    _id = await db.fetch_val(
        """
        INSERT INTO users (username, email, password_hash) VALUE (:u, :e, :p) RETURNING id
        """,
        values=dict(u=username, e=email, p=pwd_hash)
    )
    User = namedtuple("User", ["username", "email", "password", "id"])
    yield User(username=username, password=password, email=email, id=_id)
    await db.execute(
        """
        DELETE FROM users WHERE id = :id
        """,
        values=(dict(id=_id))
    )


@pytest.fixture
async def verified_user(db, user):
    await db.execute("UPDATE users SET verified = 1 WHERE username = :user", values=dict(user=user.username))
    yield user
