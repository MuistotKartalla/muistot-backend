from hashlib import sha1, sha256
from secrets import token_urlsafe, compare_digest

import headers
from redis import Redis
from starlette import status
from starlette.exceptions import HTTPException
from starlette.responses import Response

from .email import (
    fetch_user_by_email,
    verify,
    is_verified,
)
from .session import load_session_data, try_create_user
from ...database import Database
from ...logging import log
from ...mailer import Mailer
from ...security import SessionManager, Session


def create_token():
    return token_urlsafe(150)


def hash_token(token: str):
    return sha256(token.encode()).hexdigest()


async def check_token(token: str, verifier: str) -> bool:
    try:
        token = hash_token(token)
        if verifier is not None and compare_digest(token, verifier):
            return True
    except UnicodeEncodeError:
        pass
    return False


async def start_session(username: str, db: Database, sm: SessionManager) -> Response:
    token = sm.start_session(
        Session(
            user=username,
            data=await load_session_data(username, db)
        )
    )
    await db.execute(
        """
        CALL log_login(:user)
        """,
        values=dict(user=username),
    )
    return Response(
        status_code=status.HTTP_200_OK,
        headers={headers.AUTHORIZATION: f"bearer {token}"},
    )


def create_token_key(username: str):
    return f'email:user:token:{sha1(username.encode()).hexdigest()}'


def fetch_login_token(username: str, redis: Redis) -> str:
    key = create_token_key(username)
    token = redis.get(key)
    limit = redis.decr(f'{key}:limit')
    if limit >= 0 and token:
        return token.decode()


def create_login_token(username: str, redis: Redis) -> str:
    token = create_token()
    key = create_token_key(username)
    redis.set(key, hash_token(token).encode(), ex=5 * 60)
    redis.set(f'{key}:limit', 3, ex=5 * 60)
    return token


def clear_login_token(username: str, redis: Redis):
    redis.delete(f'email:user:token:{sha1(username.encode()).hexdigest()}')


def create_timeout_key(email: str):
    return f'email:timeout:{sha1(email.encode()).hexdigest()}'


def check_email_timeout(email: str, redis: Redis):
    return not redis.exists(create_timeout_key(email))


def start_email_timeout(email: str, redis: Redis):
    return not redis.set(create_timeout_key(email), '', ex=60)


async def send_login_email(
        email: str,
        username: str,
        verified: bool,
        lang: str,
        mailer: Mailer,
        redis: Redis,
):
    start_email_timeout(email, redis)
    token = create_login_token(username, redis)
    result = await mailer.send_email(
        email,
        "login",
        user=username,
        token=token,
        lang=lang,
        verified=verified,
    )
    if not result.success:
        log.error("Failed to send mail: %s", result.reason)


async def start_email_login(
        email: str,
        db: Database,
        lang: str,
        mailer: Mailer,
        redis: Redis,
) -> Response:
    username = await fetch_user_by_email(email, db)
    if username is None:
        username = await try_create_user(email, db)
    if check_email_timeout(email, redis):
        await send_login_email(email, username, await is_verified(username, db), lang, mailer, redis)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    else:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many emails")


async def complete_email_login(
        username: str,
        token: str,
        db: Database,
        sm: SessionManager,
        redis: Redis,
) -> Response:
    if await check_token(token, fetch_login_token(username, redis)):
        clear_login_token(username, redis)
        if not await is_verified(username, db):
            await verify(username, db)
        return await start_session(username, db, sm)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
