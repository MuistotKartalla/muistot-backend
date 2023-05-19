import time
from urllib.parse import urlencode

import httpx
import pytest
from fastapi import status, HTTPException
from headers import AUTHORIZATION, CONTENT_LANGUAGE

from muistot.config import Config
from muistot.login.logic.email import fetch_user_by_email
from muistot.login.logic.login import check_email_timeout, create_timeout_key, create_login_token
from muistot.login.logic.login import send_login_email, try_create_user

AUTH_PREFIX = "/auth"
STATUS = AUTH_PREFIX + "/status"
EMAIL_LOGIN = AUTH_PREFIX + "/email"
EMAIL_EXCHANGE = AUTH_PREFIX + "/email/exchange"


@pytest.mark.anyio
async def test_email(capture_mail, user, cache_redis):
    await send_login_email(user.email, user.username, "en", capture_mail, cache_redis)
    data = capture_mail[("login", user.email)]

    assert "token" in data
    assert data["user"] == user.username


@pytest.mark.anyio
async def test_email_timeout(user, capture_mail, cache_redis):
    await send_login_email(user.email, user.username, "en", capture_mail, cache_redis)
    assert not check_email_timeout(user.email, cache_redis)
    cache_redis.set(create_timeout_key(user.email), '', ex=1)
    time.sleep(1.1)
    assert check_email_timeout(user.email, cache_redis)


@pytest.mark.anyio
async def fetch_user(db, user):
    assert (await fetch_user_by_email(user.email, db)) == user.username
    assert (await fetch_user_by_email('a', db)) is None
    assert (await fetch_user_by_email(None, db)) is None


@pytest.mark.anyio
async def test_verifier(user, cache_redis):
    token = create_login_token(user.username, cache_redis)
    assert token is not None
    assert cache_redis.dbsize() == 2  # Token and usage counter


@pytest.mark.anyio
async def test_create_fails_on_duplicate(db, user):
    """If generation fails all the time the application should still handle the scenario
    """
    with pytest.raises(HTTPException) as e:
        await try_create_user(user.email, db)
    assert e.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.anyio
async def test_email_login_timeout(non_existent_email, client, cache_redis):
    r = await client.post(f"{EMAIL_LOGIN}?email={non_existent_email}")
    assert r.status_code == status.HTTP_204_NO_CONTENT

    # Check cache rate limits the request
    r = await client.post(f"{EMAIL_LOGIN}?email={non_existent_email}")
    assert r.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.anyio
async def test_email_login_max_tries(non_existent_email, client, cache_redis, capture_mail):
    r = await client.post(f"{EMAIL_LOGIN}?email={non_existent_email}")
    assert r.status_code == status.HTTP_204_NO_CONTENT

    mail = capture_mail[("login", non_existent_email)]
    token = mail["token"]
    user = mail["user"]

    for _ in range(3):
        # Clear email rate limits
        cache_redis.delete(*cache_redis.keys('email-login:*'))
        r = await client.post(f"{EMAIL_EXCHANGE}?{urlencode(dict(user=user, token=token[:-1]))}")
        assert r.status_code == status.HTTP_404_NOT_FOUND

    # Clear email rate limits
    cache_redis.delete(*cache_redis.keys('email-login:*'))
    # Assert after decrementing the key a few time we will not be able to log in with the correct token
    r = await client.post(f"{EMAIL_EXCHANGE}?{urlencode(dict(user=user, token=token))}")
    assert r.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.anyio
async def test_email_login_new_user(non_existent_email, client):
    r = await client.post(f"{EMAIL_LOGIN}?email={non_existent_email}")
    assert r.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.anyio
async def test_email_login_full(non_existent_email, client, capture_mail):
    r = await client.post(f"{EMAIL_LOGIN}?email={non_existent_email}")
    assert r.status_code == status.HTTP_204_NO_CONTENT, r.text

    mail = capture_mail[("login", non_existent_email)]
    token = mail["token"]
    user = mail["user"]

    r = await client.post(f"{EMAIL_EXCHANGE}?{urlencode(dict(user=user, token=token))}")
    assert r.status_code == status.HTTP_200_OK
    assert AUTHORIZATION in r.headers
    auth = r.headers[AUTHORIZATION]

    r = await client.get(STATUS, headers={AUTHORIZATION: auth})
    assert r.status_code == status.HTTP_200_OK


@pytest.mark.anyio
async def test_email_token_not_exists(client, non_existent_email, capture_mail):
    r = await client.post(f"{EMAIL_LOGIN}?email={non_existent_email}")
    assert r.status_code == status.HTTP_204_NO_CONTENT

    mail = capture_mail[("login", non_existent_email)]
    token = mail["token"]
    user = mail["user"]

    r = await client.post(f"{EMAIL_EXCHANGE}?{urlencode(dict(user=user, token=token[:-2]))}")
    assert r.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.anyio
async def test_email_token_not_exists_not_unicode(client, user, capture_mail):
    r = await client.post(f"{EMAIL_EXCHANGE}?{urlencode(dict(user=user.username, token='ööööööääääää'))}")
    assert r.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.anyio
async def test_namegen_no_more_names(client, user, non_existent_email, capture_mail):
    with httpx.Client(base_url=Config.namegen.url) as c:
        c.post(f"/lock?{urlencode(dict(username=user.username))}")
        try:
            r = await client.post(f"{EMAIL_LOGIN}?{urlencode(dict(email=non_existent_email))}")
            assert r.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        finally:
            c.post("/lock")


@pytest.mark.anyio
async def test_namegen_failure(client, non_existent_email, capture_mail):
    with httpx.Client(base_url=Config.namegen.url) as c:
        c.post(f"/disable")
        try:
            r = await client.post(f"{EMAIL_LOGIN}?{urlencode(dict(email=non_existent_email))}")
            assert r.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        finally:
            c.post("/disable")


@pytest.mark.anyio
async def test_email_login_non_verified_verifies(user, client, capture_mail, db):
    r = await client.post(f"{EMAIL_LOGIN}?email={user.email}")
    assert r.status_code == status.HTTP_204_NO_CONTENT

    assert not await db.fetch_val(f"SELECT verified FROM users WHERE id = {user.id}")

    mail = capture_mail[("login", user.email)]
    token = mail["token"]

    r = await client.post(f"{EMAIL_EXCHANGE}?{urlencode(dict(user=user.username, token=token))}")
    assert r.status_code == status.HTTP_200_OK

    assert await db.fetch_val(f"SELECT verified FROM users WHERE id = {user.id}")


@pytest.mark.anyio
async def test_email_login_verified_ok(user, client, capture_mail, db):
    """Sanity check for user with a verified status set to True
    """
    r = await client.post(f"{EMAIL_LOGIN}?email={user.email}")
    assert r.status_code == status.HTTP_204_NO_CONTENT

    await db.execute(f"UPDATE users SET verified = 1 WHERE id = {user.id}")

    token = capture_mail[("login", user.email)]["token"]
    r = await client.post(f"{EMAIL_EXCHANGE}?{urlencode(dict(user=user.username, token=token))}")
    assert r.status_code == status.HTTP_200_OK

    assert await db.fetch_val(f"SELECT verified FROM users WHERE id = {user.id}")


@pytest.mark.anyio
@pytest.mark.parametrize("lang, expected", [
    ("en-US,en;q=0.5", "en"),
    ("fi", "fi"),
    #  ("xwadwadwa", Config.localization.default), Fails
])
async def test_email_templating_lang(user, client, capture_mail, lang, expected):
    r = await client.post(f"{EMAIL_LOGIN}?email={user.email}", headers={CONTENT_LANGUAGE: lang})
    assert r.status_code == status.HTTP_204_NO_CONTENT

    assert capture_mail[("login", user.email)]["lang"] == expected
