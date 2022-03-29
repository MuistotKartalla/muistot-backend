import urllib.parse as url

from fastapi import APIRouter, Request, Depends, Response, status, HTTPException

from ..logic.email import fetch_user_by_email, can_send_email, send_email
from ..logic.login import try_create_user, handle_login_token
from ..logic.models import EmailStr
from ...database import dba, Database

router = APIRouter(tags=["Auth"])


@router.post(
    "/login/email-only",
    status_code=204,
    response_class=Response,
    responses={
        200: {"description": "Successful login"},
        400: {"description": "Bad request"},
    }
)
async def email_only_login(email: EmailStr, db: Database = Depends(dba)):
    username = await fetch_user_by_email(email, db)
    if username is None:
        username = await try_create_user(email, db)
    if await can_send_email(email, db):
        await send_email(username, db)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    else:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS)


@router.post(
    "/login/email-only/exchange",
    status_code=200,
    response_class=Response,
    responses={
        200: {"description": "Successful login"},
        404: {"description": "Token not found"}
    }
)
async def exchange_code(r: Request, user: str, token: str, db: Database = Depends(dba)) -> Response:
    return await handle_login_token(url.unquote(user), token, db, r.state.manager)
