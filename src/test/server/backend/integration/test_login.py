import pytest
from fastapi import status


@pytest.fixture
async def non_existent_email(db, anyio_backend):
    email = "does_not_Exist_in_tests@example.com"
    yield email
    await db.execute("DELETE FROM users WHERE email = :email", values=dict(email=email))


@pytest.fixture
async def login_url(db, client, users, anyio_backend):
    from urllib.parse import quote
    client.app.state.FastStorage.redis.flushdb()
    await db.execute("DELETE FROM user_email_verifiers")
    yield f"/login/email-only?email={quote(users[-1].email)}"
    client.app.state.FastStorage.redis.flushdb()
    await db.execute("DELETE FROM user_email_verifiers")


@pytest.mark.anyio
async def test_email_login_timeout(login_url, client, db, users):
    r = client.post(login_url)
    assert r.status_code == status.HTTP_204_NO_CONTENT

    await db.execute("DELETE FROM user_email_verifiers")

    r = client.post(login_url)
    assert r.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.anyio
async def test_email_login_timeout_no_cache(login_url, client, db):
    r = client.post(login_url)
    assert r.status_code == status.HTTP_204_NO_CONTENT

    client.app.state.FastStorage.redis.flushdb()

    r = client.post(login_url)
    assert r.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.anyio
async def test_email_login_new_user(non_existent_email, client, db):
    r = client.post(f"/login/email-only?email={non_existent_email}")
    assert r.status_code == status.HTTP_204_NO_CONTENT
