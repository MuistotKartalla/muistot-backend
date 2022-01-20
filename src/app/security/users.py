from typing import Optional

from fastapi import HTTPException
from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import scopes
from .jwt import generate_jwt
from .password import check_password, hash_password
from .. import headers
from ..database import Database
from ..mailer import get_mailer


class LoginQuery(BaseModel):
    username: Optional[str]
    email: Optional[str]
    password: str


class RegisterQuery(BaseModel):
    username: str
    email: str
    password: str


async def handle_login(db: Database, m, login: LoginQuery) -> JSONResponse:
    if m is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bad Request")
    username: str = m[0]
    stored_hash: str = m[1]
    verified = m[2] == 1
    if check_password(password_hash=stored_hash, password=login.password):
        admin_list = [m[0] async for m in db.iterate(
            """
            SELECT p.name
            FROM users u
                JOIN project_admins pa ON pa.user_id = u.id
                JOIN projects p ON pa.project_id = p.id
            WHERE u.username = :username
            """,
            values=dict(username=username)
        )]
        token = generate_jwt({
            scopes.SUBJECT: username,
            scopes.AUTHENTICATED: True,
            **({
                   scopes.ADMIN: True,
                   scopes.PROJECTS: admin_list
               } if len(admin_list) > 0 else {}),
            **({
                   scopes.SUPERUSER: True,
               } if m[3] == 1 else {})
        })
        res = JSONResponse(
            status_code=status.HTTP_200_OK,
            headers={headers.AUTHORIZATION: f'bearer {token}'}
        )
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bad Request")
    if not verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not verified")
    else:
        return res


async def login_username(login: LoginQuery, db: Database) -> JSONResponse:
    return await handle_login(
        db,
        await db.fetch_one(
            """
            SELECT u.username, u.password_hash, u.verified, su.user_id IS NOT NULL
            FROM users u
                LEFT JOIN superusers su ON su.user_id = u.id
            WHERE u.username=:uname
            """,
            values=dict(uname=login.username)
        ),
        login
    )


async def login_email(login: LoginQuery, db: Database) -> JSONResponse:
    return await handle_login(
        db,
        await db.fetch_one(
            """
            SELECT u.username, u.password_hash, u.verified, su.user_id IS NOT NULL
            FROM users u
                LEFT JOIN superusers su ON su.user_id = u.id
            WHERE u.email=:email
            """,
            values=dict(email=login.email)
        ),
        login
    )


async def register_user(user: RegisterQuery, db: Database) -> JSONResponse:
    mailer = get_mailer()
    if not await mailer.verify_email(user.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bad Email")
    m = await db.fetch_one(
        "SELECT"
        "   EXISTS(SELECT 1 FROM users WHERE username=:uname), "
        "   EXISTS(SELECT 1 FROM users WHERE email=:email)",
        values=dict(uname=user.username, email=user.email)
    )
    username_taken = m[0] == 1
    email_taken = m[1] == 1
    if username_taken:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already in use")
    elif email_taken:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
    else:
        await db.execute(
            "INSERT INTO users (email, username, password_hash) VALUE (:email, :user, :password)",
            values=dict(email=user.email, user=user.username, password=hash_password(password=user.password))
        )
        await mailer.send_verify_email(user.username, user.email)
        return JSONResponse(status_code=status.HTTP_201_CREATED)


__all__ = [
    'login_email',
    'login_username',
    'LoginQuery',
    'RegisterQuery',
    'register_user'
]
