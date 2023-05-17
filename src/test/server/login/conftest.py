from collections import namedtuple
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from muistot import mailer
from muistot.config import Config
from muistot.login import login_router
from muistot.middleware import SessionMiddleware, LanguageMiddleware

User = namedtuple("User", ["username", "email", "id"])


@pytest.fixture(autouse=True)
def capture_mail():
    captured_data = {}

    class Capturer(mailer.Mailer):

        async def send_email(self, email: str, email_type: str, **data: dict) -> mailer.Result:
            captured_data[(email_type, email)] = data
            return mailer.Result(success=True)

        def __getitem__(self, item):
            return captured_data[item]

    yield Capturer()


@pytest.fixture
async def client(db_instance, cache_redis, capture_mail):
    app = FastAPI()
    app.include_router(login_router, prefix="/auth")
    app.dependency_overrides[mailer.get_mailer] = lambda: capture_mail

    app.add_middleware(
        SessionMiddleware,
        url=Config.sessions.redis_url,
        token_bytes=Config.sessions.token_bytes,
        lifetime=Config.sessions.token_lifetime,
    )

    app.add_middleware(
        LanguageMiddleware,
        default_language=Config.localization.default,
        languages=Config.localization.supported,
    )

    # Replaces redis and databases
    @app.middleware("http")
    async def _(request, call_next):
        request.state.redis = cache_redis
        request.state.databases = SimpleNamespace(default=db_instance)
        return await call_next(request)

    client = AsyncClient(app=app, base_url="http://test")
    async with client as client_session:
        yield client_session

    cache_redis.flushdb()


@pytest.fixture
async def non_existent_email(db, client):
    email = "does_not_Exist_in_tests@example.com"
    yield email
    await db.execute("DELETE FROM users WHERE email = :email", values=dict(email=email))


@pytest.fixture
async def user(db, client):
    email = "login_test_123213123213u21389213u21321@example.com"
    username = "test_login_user#9013"
    _id = await db.fetch_val(
        """
        INSERT INTO users (username, email) VALUE (:u, :e) RETURNING id
        """,
        values=dict(u=username, e=email)
    )
    yield User(username=username, email=email, id=_id)
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
