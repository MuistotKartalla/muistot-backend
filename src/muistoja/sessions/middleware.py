from typing import Optional, Tuple

from headers import AUTHORIZATION
from starlette.middleware.authentication import AuthCredentials
from starlette.middleware.authentication import (
    AuthenticationBackend,
    AuthenticationError,
)
from starlette.requests import HTTPConnection

from .manager import SessionManager
from ..security import User, scopes


class SessionManagerMiddleware(AuthenticationBackend):
    def __init__(self, manager: SessionManager):
        self.manager = manager

    async def authenticate(
            self, request: HTTPConnection
    ) -> Optional[Tuple[AuthCredentials, User]]:
        """Extracts Session data from requests

        Adds a property to the request state to access the SessionManager

        r.state.manager: SessionManager
        """
        header = request.headers.get(AUTHORIZATION, None)
        if header is not None:
            scheme, _, credentials = header.partition(" ")
            if scheme.lower() != "bearer":
                raise AuthenticationError("Wrong Scheme")
            try:
                session = self.manager.get_session(credentials)
                user = User(username=session.user, token=credentials)
                session_data = session.data
                if "projects" in session_data:
                    user.admin_projects = set(session_data["projects"])
                creds = AuthCredentials(scopes.AUTHENTICATED)
                request.scope["session"] = session_data
                if "scopes" in session_data:
                    creds.scopes.append(session_data["scopes"])
                    user.scopes.update(session_data["scopes"])
            except ValueError as e:
                raise AuthenticationError(
                    e.args[0] if len(e.args) > 0 else "Invalid Token"
                )
        else:
            user = User()
            creds = AuthCredentials()
        request.state.manager = self.manager
        return creds, user


__all__ = ["SessionManagerMiddleware"]
