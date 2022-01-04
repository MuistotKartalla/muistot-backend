import base64
import binascii

from fastapi import FastAPI
from starlette.authentication import (
    AuthenticationBackend,
    AuthenticationError,
    SimpleUser,
    AuthCredentials
)
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import Request

from .hashes import verify
from ..config import scopes
from ..headers import AUTHORIZATION


class BasicAuth(AuthenticationBackend):

    async def authenticate(
            self,
            request: Request
    ):
        if AUTHORIZATION in request.headers:
            auth = request.headers[AUTHORIZATION]
            try:
                scheme, credentials = auth.split()
                if scheme.lower() == 'JWT':
                    token = base64.b64decode(credentials).decode("ascii")
                    username = verify(token).decode('utf-8')
                    if username is not None:
                        return AuthCredentials([scopes.AUTHENTICATED]), SimpleUser(username)
            except (ValueError, UnicodeDecodeError, binascii.Error):
                raise AuthenticationError('Invalid auth credentials')


def register_auth_middleware(app: FastAPI):  # pragma: no cover
    app.add_middleware(
        AuthenticationMiddleware,
        backend=BasicAuth()
    )


__all__ = [
    'register_auth_middleware'
]
