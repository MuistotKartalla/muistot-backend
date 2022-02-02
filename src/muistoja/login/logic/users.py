from typing import Optional, Tuple, Callable

from fastapi import HTTPException
from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..mailer import get_mailer
from ...core import headers
from ...core.database import Database
from ...core.security import scopes
from ...core.security.jwt import generate_jwt
from ...core.security.password import check_password, hash_password


class LoginQuery(BaseModel):
    username: Optional[str]
    email: Optional[str]
    password: str


class RegisterQuery(BaseModel):
    username: str
    email: str
    password: str


async def to_token_response(username: str, superuser: bool, db: Database):
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
           } if superuser else {})
    })
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        headers={headers.AUTHORIZATION: f'bearer {token}'}
    )


async def handle_login(db: Database, m, login: LoginQuery) -> JSONResponse:
    if m is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bad Request")
    username: str = m[0]
    stored_hash: str = m[1]
    verified = m[2] == 1
    if check_password(password_hash=stored_hash, password=login.password):
        res = await to_token_response(username, m[3] == 1, db)
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
        return JSONResponse(status_code=status.HTTP_201_CREATED)


async def create_email_verifier(user: str, db: Database) -> Tuple[str, str]:
    from secrets import token_urlsafe
    token = token_urlsafe(150)
    await db.execute(
        """
        REPLACE INTO user_email_verifiers (user_id, verifier) 
        SELECT id, :token 
        FROM users
        WHERE username = :user
        """,
        values=dict(user=user, token=token)
    )
    email = await db.fetch_val(
        """
        SELECT email FROM users WHERE username = :user
        """,
        values=dict(user=user)
    )
    return email, token


async def send_email(
        user: str,
        url_generator: Callable[[str, str], str],
        db: Database,
        lang: str = 'fi-register'
):
    from ..mailer import get_mailer
    email, token = await create_email_verifier(user, db)
    mailer = get_mailer()
    await mailer.send_email(
        email,
        user=user,
        url=url_generator(user, token),
        lang=lang
    )


async def handle_login_token(user: str, token: str, db: Database) -> JSONResponse:
    from secrets import compare_digest
    db_token = await db.fetch_val(
        """
        SELECT uev.verifier
        FROM user_email_verifiers uev 
            JOIN users u ON uev.user_id = u.id
                AND u.username = :user
        WHERE TIMESTAMPDIFF(MINUTE, uev.created_at, CURRENT_TIMESTAMP) < 10
        """,
        values=dict(user=user)
    )
    if db_token is not None and compare_digest(token, db_token):
        m = await db.fetch_one(
            """
            SELECT u.username, su.user_id IS NOT NULL, u.verified
            FROM users u
                LEFT JOIN superusers su ON su.user_id = u.id
            WHERE u.username=:user
            """,
            values=dict(user=user)
        )
        res = await to_token_response(m[0], m[1] == 1, db)
        await db.execute(
            """
            DELETE uev FROM user_email_verifiers uev 
                JOIN users u ON uev.user_id = u.id
            WHERE u.username = :user
            """,
            values=dict(user=user)
        )
        if m[2] != 1:
            res.headers['Muistot-Change-Username'] = 'true'
        return res
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')


__all__ = [
    'login_email',
    'login_username',
    'LoginQuery',
    'RegisterQuery',
    'register_user',
    'handle_login_token',
    'send_email'
]
