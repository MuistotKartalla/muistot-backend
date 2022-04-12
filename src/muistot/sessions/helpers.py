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


def on_error(_: Request, exc: AuthenticationError):
    """Customizes the authentication errors"""
    try:
        message = exc.__cause__.args[0]
    except (AttributeError, IndexError):
        message = "Error in Authentivation"
    return ErrorResponse(error=ApiError(code=status.HTTP_401_UNAUTHORIZED, message=message))


def add_session_manager(app: FastAPI):
    """Adds Redis session management to the app"""
    session_manager = SessionManager(
        redis_url=Config.sessions.redis_url,
        token_bytes=Config.sessions.token_bytes,
        lifetime=Config.sessions.token_lifetime,
    )
    """Simple session manger added to all requests to supply user data.
    """
    app.state.SessionManager = session_manager
    app.add_middleware(
        AuthenticationMiddleware,
        backend=SessionManagerMiddleware(session_manager),
        on_error=on_error,
    )


__all__ = ["add_session_manager"]
