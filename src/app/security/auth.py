import binascii
from typing import Dict, Set, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from starlette.authentication import BaseUser

from . import scopes
from .jwt import read_jwt
from ..models import PID

auth_scheme = HTTPBearer(
    bearerFormat='Verified Claims',
    description='Contains Username and Validity intervals with a verifier',
)


class User(BaseModel, BaseUser):
    username: Optional[str]
    scopes: Set[str] = Field(default_factory=lambda: set())
    admin_projects: Set[PID] = Field(default_factory=lambda: set())

    @property
    def is_superuser(self) -> bool:
        return scopes.SUPERUSER in self.scopes

    @property
    def identity(self) -> str:
        return self.username or '! not authenticated !'

    @property
    def display_name(self) -> str:
        return self.identity

    @property
    def is_authenticated(self) -> bool:
        return scopes.AUTHENTICATED in self.scopes

    def is_admin_in(self, project: PID) -> bool:
        """
        This should be faster than querying DB every time we need to check if someone is an Admin.
        Only verifying from DB should be ok, but initial rejection based on JWT should save time.

        :param project: PID
        :return: Bool
        """
        return project in self.admin_projects or self.is_superuser


def get_user(r: Request, token: HTTPAuthorizationCredentials = Depends(auth_scheme)) -> User:
    try:
        if r.state.resolved:
            return r.user
        if token.scheme != 'bearer':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Bad Auth')
        claims: Dict = read_jwt(token.credentials)
        return User(
            username=claims[scopes.SUBJECT],
            admin_projects=set(claims[scopes.PROJECTS]) if scopes.PROJECTS in claims else set(),
            scopes={k for k in scopes.SECURITY_SCOPES if k in claims and claims[k]}
        )
    except (ValueError, UnicodeDecodeError, binascii.Error, KeyError) as e:
        from ..logging import log
        log.exception("Invalid auth", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Invalid auth credentials'
        )


def register_auth(app: FastAPI):  # pragma: no cover
    @app.middleware('http')
    async def mock_ware(r, call_next):
        """
        Adds users to all requests if header is available
        """
        from ..headers import AUTHORIZATION
        if AUTHORIZATION in r.headers:
            try:
                r.state.resolved = False
                r.scope['user'] = get_user(r, await auth_scheme(r))
                r.state.resolved = True
            except (IndexError, ValueError, HTTPException):
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST)
        else:
            r.state.resolved = False

        if 'user' not in r.scope:
            r.scope['user'] = User()

        return await call_next(r)


def require_auth(*required_scopes: str):
    from functools import wraps

    def actual_auth_thingy(f):
        import inspect

        # Check that the scope is actually probably maybe used
        if next(iter(inspect.signature(f).parameters.values())).annotation != Request:
            assert False, f'Request (r) parameter is not found for function {f.__name__}. Should be first.'

        user_param = None
        ok = False
        for a in inspect.signature(f).parameters.values():
            if a.annotation == User:
                user_param = a.name
                ok = True

        @wraps(f)
        async def check_auth(r: Request, *args, **kwargs):
            from fastapi import HTTPException
            try:
                if user_param is None:
                    user: User = kwargs.pop('__auth_helper__')
                else:
                    user = kwargs[user_param]
                if user_param is not None:
                    kwargs[user_param] = user
                for scope in required_scopes:
                    if scope not in user.scopes:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f'Unauthorized\n'
                                   f'Required ({",".join(required_scopes)})\n'
                                   f'Got ({",".join(user.scopes)})'
                        )
                r.scope['user'] = user
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise e
                from ..logging import log
                log.exception(f"Failed auth check: {repr(r.headers)}", exc_info=e)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Unauthorized\nValidation Failed'
                )
            return await f(r, *args, **kwargs)

        if not ok:
            s: inspect.Signature = inspect.signature(check_auth)
            s = s.replace(parameters=[*s.parameters.values(), inspect.Parameter(
                '__auth_helper__',
                inspect.Parameter.KEYWORD_ONLY,
                default=Depends(get_user),
                annotation=User
            )])
            check_auth.__signature__ = s

        return check_auth

    return actual_auth_thingy


__all__ = [
    'register_auth',
    'require_auth',
    'User'
]
