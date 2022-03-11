"""
Supplies dependencies needed for session resolution.
"""

from fastapi import Request, FastAPI, status
from starlette.middleware.authentication import AuthenticationError
from starlette.middleware.authentication import AuthenticationMiddleware

from .manager import SessionManager
from .middleware import SessionManagerMiddleware
from ..config import Config
from ..errors import ErrorResponse, ApiError

session_manager = SessionManager(
    redis_url=Config.security.session_redis,
    token_bytes=Config.security.session_token_bytes,
    lifetime=Config.security.session_lifetime,
)
"""Simple session manger added to all requests to supply user data.
"""


def on_error(_: Request, exc: AuthenticationError):
    """Customizes the authentication errors"""
    message = exc.args[0] if len(exc.args) >= 1 else "Error in auth"
    return ErrorResponse(error=ApiError(code=status.HTTP_401_UNAUTHORIZED, message=message))


def add_session_manager(app: FastAPI):
    """Adds Redis session management to the app"""
    app.add_middleware(
        AuthenticationMiddleware,
        backend=SessionManagerMiddleware(session_manager),
        on_error=on_error,
    )


__all__ = ["add_session_manager"]
