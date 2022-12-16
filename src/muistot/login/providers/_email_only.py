import urllib.parse as url

from fastapi import APIRouter, Request, Depends, Response

from ..logic.login import handle_login_token, email_login
from ..logic.models import EmailStr
from ..logic.utils import ratelimit_via_redis_host_and_key
from ...database import Databases, Database
from ...security import disallow_auth
from ...backend.repos.base.utils import extract_language

router = APIRouter(tags=["Auth"])


@router.post(
    "/email",
    status_code=204,
    response_class=Response,
    responses={
        200: {"description": "Successful login"},
        400: {"description": "Bad request"},
        403: {"description": "Already logged in"},
    }
)
@disallow_auth
async def email_only_login(r: Request, email: EmailStr, db: Database = Depends(Databases.default)):
    ratelimit_via_redis_host_and_key(r, email)
    return await email_login(email, db, lang=extract_language(r, default_on_invalid=True))


@router.post(
    "/email/exchange",
    status_code=200,
    response_class=Response,
    responses={
        200: {"description": "Successful login"},
        404: {"description": "Token not found"}
    }
)
@disallow_auth
async def exchange_code(r: Request, user: str, token: str, db: Database = Depends(Databases.default)) -> Response:
    return await handle_login_token(url.unquote(user), token, db, r.state.manager)
