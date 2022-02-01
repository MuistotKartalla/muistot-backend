from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from ..logic import *
from ...core.database import dba, Depends, Database
from ...core.errors import Error
from ...core.headers import *

router = APIRouter()


def lang(request: Request):
    from ...core.headers import ACCEPT_LANGUAGE
    _lang = request.headers.get(ACCEPT_LANGUAGE, 'fi')
    return 'en-register' if 'fi' not in _lang else 'fi-register'


@router.post("/login", tags=["Auth"])
async def default_login(login: LoginQuery, db: Database = Depends(dba)) -> JSONResponse:
    if login.username is not None:
        return await login_username(login, db)
    elif login.email is not None:
        return await login_email(login, db)
    else:
        raise HTTPException(status_code=400, detail="Email or username required")


@router.post(
    "/register",
    responses={
        '409': {
            'model': Error,
            "description": "User already exists or email/username is in use"
        }
    },
    tags=["Auth"]
)
async def default_register(request: Request, query: RegisterQuery, db: Database = Depends(dba)) -> JSONResponse:
    import urllib.parse as url
    if AUTHORIZATION in request:
        return JSONResponse(status_code=409, content="Already signed-in")
    resp = await register_user(query, db)
    if resp.status_code == 201:
        await send_email(
            query.username,
            lambda user, token: router.url_path_for('register_confirm').make_absolute_url(
                request.base_url
            ) + f"?{url.urlencode(dict(user=user, token=token))}",
            db,
            lang=f'{lang(request)}-register'
        )
    return resp


@router.post(
    "/register/confirm",
    tags=["Auth"]
)
async def register_confirm(_: Request, user: str, token: str, db: Database = Depends(dba)) -> JSONResponse:
    if len(token) != 200:
        raise HTTPException(status_code=404)
    await db.execute(
        """
        UPDATE users u 
            JOIN user_email_verifiers uev ON uev.user_id = u.id 
        SET verified = 1
        WHERE u.username = :user AND uev.verifier = :token
        """,
        values=dict(user=user, token=token)
    )
    if (await db.fetch_val("SELECT ROW_COUNT()")) == 1:
        await db.execute(
            """
            DELETE FROM user_email_verifiers WHERE user_id = (SELECT id FROM users WHERE username = :user)
            """,
            values=dict(user=user)
        )
        return JSONResponse(status_code=204)
    else:
        raise HTTPException(status_code=404)
