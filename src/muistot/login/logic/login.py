import headers
import httpx
from fastapi import HTTPException
from fastapi import status
from fastapi.responses import Response

from .data import check_token
from .email import (
    fetch_user_by_email,
    can_send_email,
    verify,
    is_verified,
    delete_verifiers,
    create_email_verifier,
    fetch_verifier,
)
from .session import load_session_data
from ...config import Config
from ...database import Database
from ...mailer import get_mailer
from ...security import SessionManager, Session


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


async def register_user(username: str, email: str, db: Database) -> Response:
    m = await db.fetch_one(
        "SELECT"
        "   EXISTS(SELECT 1 FROM users WHERE username=:uname), "
        "   EXISTS(SELECT 1 FROM users WHERE email=:email)",
        values=dict(
            uname=username,
            email=email,
        ),
    )
    username_taken = m[0] == 1
    email_taken = m[1] == 1
    if username_taken:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already in use"
        )
    elif email_taken:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already in use"
        )
    else:
        await db.execute(
            "INSERT INTO users (email, username) VALUE (:email, :user)",
            values=dict(
                email=email,
                user=username,
            ),
        )
        return Response(status_code=status.HTTP_201_CREATED)


async def complete_email_login(username: str, token: str, db: Database, sm: SessionManager) -> Response:
    if await check_token(token, await fetch_verifier(username, db)):
        if not await is_verified(username, db):
            await verify(username, db)
        await delete_verifiers(username, db)
        return await start_session(username, db, sm)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


async def send_login_email(username: str, db: Database, lang: str):
    email, token, verified = await create_email_verifier(username, db)
    mailer = get_mailer()
    await mailer.send_email(
        email,
        "login",
        user=username,
        token=token,
        verified=verified,
        lang=lang,
    )


async def try_create_user(email: str, db: Database) -> str:
    async with httpx.AsyncClient(base_url=Config.namegen.url) as client:
        for _ in range(0, 5):
            try:
                r = await client.get("/")
                if r.status_code != 200:
                    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
                username = r.json()["value"]
                await register_user(username, email, db)
                return username
            except HTTPException as e:
                if e.status_code == 409:
                    pass
                else:
                    raise e
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


async def start_email_login(email: str, db: Database, lang: str) -> Response:
    username = await fetch_user_by_email(email, db)
    if username is None:
        username = await try_create_user(email, db)
    if await can_send_email(email, db):
        await send_login_email(username, db, lang)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    else:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many emails")
