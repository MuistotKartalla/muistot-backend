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
from ..middleware.database import DatabaseMiddleware, Database
from ..middleware.language import LanguageMiddleware
from ..middleware.mailer import MailerMiddleware, Mailer
from ..middleware.session import SessionMiddleware, SessionManager, User
from ..middleware.storage import RedisMiddleware, Redis

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
def get_status(
        r: Request,
        redis: Redis = Depends(RedisMiddleware.get),
        user: User = Depends(SessionMiddleware.user),
):
    ratelimit(redis, "status", r.client.host, ttl_seconds=1)
    return Response(status_code=200 if user.is_authenticated else 401)


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
async def email_only_login(
        r: Request,
        email: EmailStr,
        mailer: Mailer = Depends(MailerMiddleware.get),
        redis: Redis = Depends(RedisMiddleware.get),
        user: User = Depends(SessionMiddleware.user),
        db: Database = Depends(DatabaseMiddleware.default),
        language: str = Depends(LanguageMiddleware.get),
):
    if user.is_authenticated:
        raise HTTPException(status_code=403, detail="Already logged in")
    ratelimit(redis, "exchange", r.client.host, email, ttl_seconds=6)
    return await start_email_login(email, db, lang=language, mailer=mailer)


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
async def exchange_code(
        r: Request,
        user: str,
        token: str,
        redis: Redis = Depends(RedisMiddleware.get),
        db: Database = Depends(DatabaseMiddleware.default),
        user_instance: User = Depends(SessionMiddleware.user),
        sm: SessionManager = Depends(SessionMiddleware.get),
) -> Response:
    if user_instance.is_authenticated:
        raise HTTPException(status_code=403, detail="Already logged in")
    ratelimit(redis, "login", r.client.host, user, ttl_seconds=6)
    return await complete_email_login(url.unquote(user), token, db, sm)
