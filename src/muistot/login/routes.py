"""
Requires the following middleware:

- LanguageMiddleware
- RedisMiddleware
- SessionMiddleware
- DatabaseMiddleware
"""

import urllib.parse as url
from textwrap import dedent

from fastapi import APIRouter, Request, Response, HTTPException, Depends
from pydantic import EmailStr

from .logic import complete_email_login, start_email_login, ratelimit
from ..mailer import Mailer, get_mailer

router = APIRouter(tags=["Auth"])


@router.get(
    "/status",
    response_class=Response,
    responses={
        200: {"description": "Logged in"},
        401: {"description": "Not logged in"},
    },
    description=dedent(
        """
        Can be used to check the current authentication status of the user.
        
        This method is rate limited to ~1 r/s.
        """
    ),
)
def get_status(r: Request):
    ratelimit(r.state.redis, "status", r.client.host, ttl_seconds=1)
    return Response(status_code=200 if r.user.is_authenticated else 401)


@router.post(
    "/email",
    status_code=204,
    response_class=Response,
    responses={
        204: {"description": "Successful request"},
        400: {"description": "Bad request"},
        403: {"description": "Already logged in"},
        422: {"description": "Bad parameters"},
        429: {"description": "Too many requests"},
        503: {"description": "Resources not available"},
    },
    description=dedent(
        """
        Initiates the email login process.

        This method is rate limited to ~10 r/min.
        """
    ),
)
async def email_only_login(r: Request, email: EmailStr, mailer: Mailer = Depends(get_mailer)):
    if r.user.is_authenticated:
        raise HTTPException(status_code=403, detail="Already logged in")
    ratelimit(r.state.redis, "exchange", r.client.host, email, ttl_seconds=6)
    async with r.state.databases.default() as db:
        return await start_email_login(email, db, lang=r.state.language, mailer=mailer)


@router.post(
    "/email/exchange",
    status_code=200,
    response_class=Response,
    responses={
        200: {"description": "Successful login"},
        403: {"description": "Already logged in"},
        404: {"description": "Token not found"},
        422: {"description": "Bad parameters"},
        429: {"description": "Too many requests"},
        503: {"description": "Resources not available"},
    },
    description=dedent(
        """
        Receives the email login callback.

        This method is rate limited to ~10 r/min.
        """
    ),
)
async def exchange_code(r: Request, user: str, token: str) -> Response:
    if r.user.is_authenticated:
        raise HTTPException(status_code=403, detail="Already logged in")
    ratelimit(r.state.redis, "login", r.client.host, user, ttl_seconds=6)
    async with r.state.databases.default() as db:
        return await complete_email_login(url.unquote(user), token, db, r.state.sessions)
