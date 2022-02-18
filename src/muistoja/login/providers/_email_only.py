import urllib.parse as url
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Response, status
from fastapi.responses import JSONResponse
from headers import ACCEPT_LANGUAGE
from passlib import pwd

from ..logic import *
from ..logic.namegen import generate
from ...core.database import dba, Depends, Database

router = APIRouter(tags=["Auth"])


def lang(request: Request):
    _lang = request.headers.get(ACCEPT_LANGUAGE, 'fi')
    return 'en-register' if 'fi' not in _lang else 'fi-register'


async def try_create(email: str, db: Database):
    for _ in range(0, 5):
        try:
            username = generate()
            await register_user(
                RegisterQuery(
                    username=username,
                    email=email,
                    password=pwd.genword(length=200)
                ),
                db
            )
            return username
        except HTTPException as e:
            if e.status_code == 409:
                pass
            else:
                raise e


async def fetch_user(email: str, db: Database) -> Optional[str]:
    return await db.fetch_val(
        """
        SELECT username FROM users WHERE email = :email
        """,
        values=dict(email=email)
    )


async def check_can_send(email, db: Database):
    return (await db.fetch_val(
        """
        SELECT EXISTS(
            SELECT 1
            FROM user_email_verifiers uev 
                JOIN users u on uev.user_id = u.id 
            WHERE email = :email AND TIMESTAMPDIFF(MINUTE, uev.created_at, CURRENT_TIMESTAMP) < 10
        )
        """,
        values=dict(email=email)
    )) == 0


@router.post("/login/email-only", status_code=204, response_class=Response)
async def email_only_login(request: Request, email: str, db: Database = Depends(dba)):
    username = await fetch_user(email, db)
    if username is None:
        username = await try_create(email, db)
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='username generator exhausted'
            )
    if await check_can_send(email, db):
        await send_email(
            username,
            lambda user, token: f'{router.url_path_for("exchange_code")}?{url.urlencode(dict(user=user, token=token))}',
            db,
            lang=lang(request)
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    else:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS)


@router.post("/login/email-only/exchange")
async def exchange_code(r: Request, user: str, token: str, db: Database = Depends(dba)) -> JSONResponse:
    return await handle_login_token(user, token, db, r.state.manager)
