import urllib.parse as url

from fastapi import APIRouter, Request, Depends, Response, HTTPException
from pydantic import EmailStr

from .logic.login import complete_email_login, start_email_login
from .logic.utils import ratelimit_via_redis_host_and_key
from ..database import Database

router = APIRouter(tags=["Auth"])


async def database(request: Request):
    yield request.state.database.default


@router.get("/status", response_class=Response)
def get_status(r: Request):
    if r.user.is_authenticated:
        return Response(status_code=200)
    else:
        return Response(status_code=401)


@router.post(
    "/email",
    status_code=204,
    response_class=Response,
    responses={
        200: {"description": "Successful login"},
        400: {"description": "Bad request"},
        403: {"description": "Already logged in"},
        429: {"description": "Too many requests"},
        422: {"description": "Bad parameters"},
    }
)
async def email_only_login(r: Request, email: EmailStr, db: Database = Depends(database)):
    if r.user.is_authenticated:
        raise HTTPException(status_code=403, detail="Already logged in")
    ratelimit_via_redis_host_and_key(r, "login", email, ttl_seconds=20)
    return await start_email_login(email, db, lang=r.state.language)


@router.post(
    "/email/exchange",
    status_code=200,
    response_class=Response,
    responses={
        200: {"description": "Successful login"},
        404: {"description": "Token not found"},
        429: {"description": "Too many requests"},
        422: {"description": "Bad parameters"},
    }
)
async def exchange_code(r: Request, user: str, token: str, db: Database = Depends(database)) -> Response:
    if r.user.is_authenticated:
        raise HTTPException(status_code=403, detail="Already logged in")
    ratelimit_via_redis_host_and_key(r, "exchange", user, ttl_seconds=5)
    return await complete_email_login(url.unquote(user), token, db, r.state.sessions)
