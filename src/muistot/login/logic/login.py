import headers
import httpx
from fastapi import HTTPException
from fastapi import status
from fastapi.responses import Response

from .data import load_session_data, check_token
from .email import send_confirm_email
from .models import LoginQuery, RegisterQuery, EmailStr
from ...config import Config
from ...database import Database
from ...security.password import check_password, hash_password
from ...sessions import SessionManager, Session


async def start_session(username: str, db: Database, sm: SessionManager) -> Response:
    token = sm.start_session(
        Session(
            user=username,
            data=await load_session_data(username, db)
        )
    )
    return Response(
        status_code=status.HTTP_200_OK,
        headers={headers.AUTHORIZATION: f"bearer {token}"},
    )


async def handle_login(m, login: LoginQuery, sm: SessionManager, db: Database) -> Response:
    if m is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Bad Request"
        )
    username: str = m[0]
    stored_hash: bytes = m[1]
    verified = m[2] == 1
    if check_password(password_hash=stored_hash, password=login.password):
        if not verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not verified"
            )
        return await start_session(username, db, sm)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad Request"
        )


async def login_username(login: LoginQuery, db: Database, sm: SessionManager) -> Response:
    return await handle_login(
        await db.fetch_one(
            """
            SELECT u.username, u.password_hash, u.verified
            FROM users u
            WHERE u.username=:uname
            """,
            values=dict(uname=login.username),
        ),
        login,
        sm,
        db,
    )


async def login_email(login: LoginQuery, db: Database, sm: SessionManager) -> Response:
    return await handle_login(
        await db.fetch_one(
            """
            SELECT u.username, u.password_hash, u.verified
            FROM users u
            WHERE u.email=:email
            """,
            values=dict(email=login.email),
        ),
        login,
        sm,
        db,
    )


async def register_user(user: RegisterQuery, db: Database, send_mail=True) -> Response:
    m = await db.fetch_one(
        "SELECT"
        "   EXISTS(SELECT 1 FROM users WHERE username=:uname), "
        "   EXISTS(SELECT 1 FROM users WHERE email=:email)",
        values=dict(uname=user.username, email=user.email),
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
            "INSERT INTO users (email, username, password_hash) VALUE (:email, :user, :password)",
            values=dict(
                email=user.email,
                user=user.username,
                password=hash_password(password=user.password),
            ),
        )
        if send_mail:
            await send_confirm_email(user.username, db)
        return Response(status_code=status.HTTP_201_CREATED)


async def is_verified(username: str, db: Database) -> bool:
    return await db.fetch_val("SELECT verified FROM users WHERE username = :user", values=dict(user=username))


async def verify(username: str, db: Database):
    await db.execute(
        """
        UPDATE users SET verified = 1 WHERE username = :user
        """,
        values=dict(user=username)
    )


async def delete_verifiers(username: str, db: Database):
    await db.execute(
        """
        DELETE FROM user_email_verifiers 
        WHERE user_id = (SELECT id FROM users WHERE username = :user)
        """,
        values=dict(user=username),
    )


async def handle_login_token(username: str, token: str, db: Database, sm: SessionManager) -> Response:
    if await check_token(username, token, db):
        if not await is_verified(username, db):
            await verify(username, db)
        await delete_verifiers(username, db)
        return await start_session(username, db, sm)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


async def try_create_user(email: EmailStr, db: Database) -> str:
    from secrets import token_urlsafe
    async with httpx.AsyncClient(base_url=Config.namegen.url) as client:
        for _ in range(0, 5):
            try:
                r = await client.get("/")
                if r.status_code != 200:
                    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
                username = r.json()["value"]
                await register_user(
                    RegisterQuery(
                        username=username,
                        email=email,
                        password=token_urlsafe(200),
                    ),
                    db,
                    send_mail=False,
                )
                return username
            except HTTPException as e:
                if e.status_code == 409:
                    pass
                else:
                    raise e
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


async def confirm(username: str, code: str, db: Database, sm: SessionManager):
    if await check_token(username, code, db):
        await verify(username, db)
        await delete_verifiers(username, db)
        return await start_session(username, db, sm)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


async def email_login(email: EmailStr, db: Database) -> Response:
    from .email import fetch_user_by_email, can_send_email, send_login_email
    username = await fetch_user_by_email(email, db)
    if username is None:
        username = await try_create_user(email, db)
    if await can_send_email(email, db):
        await send_login_email(username, db)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    else:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many emails")


async def password_login(login: LoginQuery, db: Database, sm: SessionManager) -> Response:
    if login.username is not None:
        return await login_username(login, db, sm)
    else:
        return await login_email(login, db, sm)


__all__ = [
    "confirm",
    "register_user",
    "handle_login_token",
    "try_create_user",
    "email_login",
    "password_login",
]
