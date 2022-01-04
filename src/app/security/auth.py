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

from .jwt import read_jwt
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
                scheme, jwt = auth.split()
                if scheme.lower() == 'JWT':
                    claims = read_jwt(jwt)
                    return AuthCredentials([scopes.AUTHENTICATED]), SimpleUser(claims['sub'])
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
