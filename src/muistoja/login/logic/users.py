from typing import Optional, Tuple, Callable

from fastapi import HTTPException
from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..mailer import get_mailer
from ...core import headers
from ...core.database import Database
from ...core.security import SessionManager
from ...core.security.password import check_password, hash_password


class LoginQuery(BaseModel):
    username: Optional[str]
    email: Optional[str]
    password: str


class RegisterQuery(BaseModel):
    username: str
    email: str
    password: str


async def load_user_data(username: str, db: Database):
    from ...core.security.scopes import SUPERUSER, ADMIN
    out = dict(scopes=set())
    is_superuser = await db.fetch_val(
        """
        SELECT EXISTS(
            SELECT 1 
            FROM users u 
                JOIN superusers su on su.user_id = u.id
            WHERE u.username = :user
        )
        """,
        values=dict(user=username)
    )
    if is_superuser:
        out['scopes'].add(SUPERUSER)
        out['scopes'].add(ADMIN)
    admined_projects = [m[0] for m in await db.fetch_all(
        """
        SELECT p.name
        FROM users u
            JOIN project_admins pa on u.id = pa.user_id
            JOIN projects p on pa.project_id = p.id
        WHERE u.username = :user
        """,
        values=dict(user=username)
    )]
    if len(admined_projects) > 0:
        out['scopes'].add(ADMIN)
        out['projects'] = admined_projects
    out['scopes'] = list(out['scopes'])
    return out


async def to_token_response(
        username: str,
        db: Database,
        sm: SessionManager
):
    token = await sm.start_session(username, await load_user_data(username, db))
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        headers={headers.AUTHORIZATION: f'bearer {token}'}
    )


async def handle_login(m, login: LoginQuery, sm: SessionManager, db: Database) -> JSONResponse:
    if m is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bad Request")
    username: str = m[0]
    stored_hash: str = m[1]
    verified = m[2] == 1
    if check_password(password_hash=stored_hash, password=login.password):
        res = await to_token_response(username, db, sm)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bad Request")
    if not verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not verified")
    else:
        return res


async def login_username(login: LoginQuery, db: Database, sm: SessionManager) -> JSONResponse:
    return await handle_login(
        await db.fetch_one(
            """
            SELECT u.username, u.password_hash, u.verified
            FROM users u
            WHERE u.username=:uname
            """,
            values=dict(uname=login.username)
        ),
        login,
        sm,
        db
    )


async def login_email(login: LoginQuery, db: Database, sm: SessionManager) -> JSONResponse:
    return await handle_login(
        await db.fetch_one(
            """
            SELECT u.username, u.password_hash, u.verified
            FROM users u
            WHERE u.email=:email
            """,
            values=dict(email=login.email)
        ),
        login,
        sm,
        db
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


async def handle_login_token(user: str, token: str, db: Database, sm: SessionManager) -> JSONResponse:
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
        res = await to_token_response(m[0], m[1] == 1, sm)
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
