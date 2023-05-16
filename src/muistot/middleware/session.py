"""
Supplies dependencies needed for session resolution.
"""

from typing import Optional, Tuple

import redis
from fastapi import status
from headers import AUTHORIZATION
from starlette.applications import ASGIApp
from starlette.middleware.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    AuthenticationMiddleware,
)
from starlette.requests import HTTPConnection

from ..errors import ErrorResponse, ApiError
from ..security import User, scopes, SessionManager


class SessionMiddleware(AuthenticationMiddleware, AuthenticationBackend):
    manager: SessionManager

    def __init__(self, app: ASGIApp, url: str, token_bytes: int, lifetime: int):
        super(SessionMiddleware, self).__init__(app, backend=self, on_error=SessionMiddleware.on_error)
        self.redis = redis.from_url(url)
        self.manager = SessionManager(redis=self.redis, token_bytes=token_bytes, lifetime=lifetime)

    def __del__(self):
        self.redis.close()

    @staticmethod
    def on_error(_: HTTPConnection, exc: AuthenticationError):
        """Customizes the authentication errors
        """
        try:
            message = exc.__cause__.args[0]
        except (AttributeError, IndexError):
            message = "Error in Authentication"
        return ErrorResponse(error=ApiError(code=status.HTTP_401_UNAUTHORIZED, message=message))

    async def authenticate(self, conn: HTTPConnection) -> Optional[Tuple[AuthCredentials, User]]:
        """Extracts Session data from requests

        Adds a property to the request state to access the SessionManager

                r.state.sessions: SessionManager
        """
        conn.state.sessions = self.manager
        header = conn.headers.get(AUTHORIZATION, None)
        if header is not None:
            scheme, _, credentials = header.partition(" ")
            if scheme.lower() != "bearer":
                raise AuthenticationError() from ValueError("Wrong Scheme")
            try:
                session = self.manager.get_session(credentials)
                user = User.from_cache(username=session.user, token=credentials)
                session_data = session.data
                if "projects" in session_data:
                    user.admin_projects = set(session_data["projects"])
                creds = AuthCredentials(scopes.AUTHENTICATED)
                conn.scope["session"] = session_data
                if "scopes" in session_data:
                    creds.scopes.append(session_data["scopes"])
                    user.scopes.update(session_data["scopes"])
            except ValueError as e:
                raise AuthenticationError from e
        else:
            user = User.null()
            creds = AuthCredentials()
        return creds, user
