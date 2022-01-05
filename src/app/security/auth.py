import binascii
from typing import Dict

from fastapi import FastAPI
from starlette.authentication import (
    AuthenticationBackend,
    AuthenticationError,
    SimpleUser,
    AuthCredentials
)
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import Request

from . import scopes
from .jwt import read_jwt
from ..headers import AUTHORIZATION
from ..models import PID


class ContainsAll:

    def __contains__(self, _):
        return True


class SuperUser(SimpleUser):

    @property
    def identity(self) -> str:
        return self.username

    # noinspection PyMethodMayBeStatic
    def is_admin_in(self, _) -> bool:
        return True


class CustomUser(SimpleUser):

    def __init__(self, data: Dict):
        super(CustomUser, self).__init__(data[scopes.SUBJECT])
        if scopes.ADMIN in data and data[scopes.ADMIN] == scopes.TRUE and scopes.ADMIN_IN_PROJECTS in data:
            self._admined_projects = set(data[scopes.ADMIN_IN_PROJECTS])
        else:
            self._admined_projects = None

    @property
    def identity(self) -> str:
        return self.username

    def is_admin_in(self, project: PID) -> bool:
        """
        This should be faster than querying DB every time we need to check if someone is an Admin.
        Only verifying from DB should be ok, but initial rejection based on JWT should save time.

        :param project: PID
        :return: Bool
        """
        return self._admined_projects is not None and project in self._admined_projects


class BasicAuth(AuthenticationBackend):

    async def authenticate(
            self,
            request: Request
    ):
        if AUTHORIZATION in request.headers:
            auth = request.headers[AUTHORIZATION]
            try:
                scheme, jwt = auth.split()
                if scheme.lower() == 'jwt':
                    claims = read_jwt(jwt)
                    user = CustomUser(claims)
                    # noinspection PyProtectedMember
                    if user._admined_projects is not None:
                        return AuthCredentials([scopes.AUTHENTICATED, scopes.ADMIN]), user
                    else:
                        return AuthCredentials([scopes.AUTHENTICATED]), user
            except (ValueError, UnicodeDecodeError, binascii.Error) as e:
                from ..logging import log
                log.exception("Invalid auth", exc_info=e)
                raise AuthenticationError('Invalid auth credentials')


def register_auth_middleware(app: FastAPI):  # pragma: no cover
    app.add_middleware(
        AuthenticationMiddleware,
        backend=BasicAuth()
    )


def require_auth(*required_scopes: str):
    from functools import wraps

    def actual_auth_thingy(f):
        import inspect

        # Check that the scope is actually probably maybe used
        ok = False
        for a in inspect.signature(f).parameters.values():
            if a.annotation == Request:
                ok = True
        assert ok, f'No Request parameter found for function {f.__name__}'

        @wraps(f)
        async def check_auth(r: Request, *args, **kwargs):
            from fastapi import HTTPException
            from starlette.authentication import has_required_scope
            try:
                if not has_required_scope(r, required_scopes):
                    raise HTTPException(
                        status_code=401,
                        detail=f'Unauthorized\n'
                               f'Required ({",".join(required_scopes)})\n'
                               f'Got ({",".join(r.auth.scopes)})'
                    )
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise e
                from ..logging import log
                log.exception(f"Failed auth check: {repr(r.headers)}", exc_info=e)
                raise HTTPException(status_code=401, detail='Unauthorized\nValidation Failed')
            return await f(r, *args, **kwargs)

        return check_auth

    return actual_auth_thingy


__all__ = [
    'register_auth_middleware',
    'require_auth',
    'CustomUser'
]
