from secrets import compare_digest

import headers
import httpx
from fastapi import HTTPException
from fastapi import status
from fastapi.responses import Response
from passlib.pwd import genword

from .data import load_session_data
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


async def register_user(user: RegisterQuery, db: Database) -> Response:
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
        return Response(status_code=status.HTTP_201_CREATED)


async def check_token(username: str, token: str, db: Database) -> bool:
    db_token = await db.fetch_val(
        """
        SELECT uev.verifier
        FROM user_email_verifiers uev 
            JOIN users u ON uev.user_id = u.id
                AND u.username = :user
        WHERE TIMESTAMPDIFF(MINUTE, uev.created_at, CURRENT_TIMESTAMP) < 10
        """,
        values=dict(user=username),
    )
    return db_token is not None and compare_digest(token, db_token)


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
        if not (await is_verified(username, db)):
            await verify(username, db)
        await delete_verifiers(username, db)
        res = await start_session(username, db, sm)
        return res
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


async def try_create_user(email: EmailStr, db: Database):
    async with httpx.AsyncClient(base_url=Config.security.namegen_url) as client:
        for _ in range(0, 5):
            try:
                username = (await client.get("/")).json()["value"]
                await register_user(
                    RegisterQuery(
                        username=username,
                        email=email,
                        password=genword(length=200)
                    ),
                    db,
                )
                return username
            except HTTPException as e:
                if e.status_code == 409:
                    pass
                else:
                    raise e
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


async def confirm(username: str, token: str, db: Database):
    if await check_token(username, token, db):
        await verify(username, db)
        await delete_verifiers(username, db)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


__all__ = [
    'confirm',
    'login_email',
    'login_username',
    'register_user',
    'handle_login_token',
    'try_create_user'
]
