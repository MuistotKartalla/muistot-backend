from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import JSONResponse

from ..logic import *
from ...core.database import dba, Depends, Database
from ...core.headers import *

router = APIRouter()


def lang(request: Request):
    from ...core.headers import ACCEPT_LANGUAGE
    _lang = request.headers.get(ACCEPT_LANGUAGE, 'fi')
    return 'en-register' if 'fi' not in _lang else 'fi-register'


@router.post("/login/email-only", status_code=204, response_class=Response)
async def email_only_login(request: Request, email: str, db: Database = Depends(dba)):
    if (await db.fetch_val(
            """
            SELECT EXISTS(SELECT 1 FROM users WHERE email = :email)
            """,
            values=dict(email=email)
    ) == 0):
        from passlib import pwd
        import random
        i = 0
        while i < 100:
            try:
                username = str(pwd.genphrase(length=2)).replace(' ', '_')
                username += '_' + pwd.getrandstr(random.SystemRandom(), '0123456789', 3)
                await register_user(
                    RegisterQuery(
                        username=username,
                        email=email,
                        password=pwd.genword(length=200)
                    ),
                    db
                )
                break
            except HTTPException as e:
                if e.status_code == 409:
                    pass
                else:
                    raise e
        if i == 100:
            raise HTTPException(status_code=500, detail='Failed to make user')
    if (await db.fetch_val(
            """
            SELECT EXISTS(
                SELECT 1
                FROM user_email_verifiers uev 
                    JOIN users u on uev.user_id = u.id 
                WHERE email = :email AND TIMESTAMPDIFF(MINUTE, uev.created_at, CURRENT_TIMESTAMP) < 10
            )
            """,
            values=dict(email=email)
    )) == 0:
        import urllib.parse as url
        await send_email(
            await db.fetch_val("SELECT username FROM users WHERE email=:email", values=dict(email=email)),
            lambda user, token: request.url_for('exchange_code') + f'?{url.urlencode(dict(user=user, token=token))}',
            db,
            lang=lang(request)
        )
        return Response(status_code=204)
    else:
        raise HTTPException(status_code=403)


@router.get("/login/email-only/exchange")
async def exchange_code(request: Request, user: str, token: str, db: Database = Depends(dba)) -> JSONResponse:
    if AUTHORIZATION in request:
        return JSONResponse(status_code=409, content="Already signed-in")
    return await handle_login_token(user, token, db)
