"""
Supplies the functions needed to do the heavy lifting in authentication
"""
import inspect
from functools import wraps
from typing import Any, Optional

from fastapi import Depends, status, HTTPException
from fastapi.security import HTTPBearer
from starlette.requests import Request

from ....middleware.session import User, SessionMiddleware


class AuthManager(HTTPBearer):
    """This marks the API as requiring Authentication
    """
    KWARG = "__auth_helper__"

    def __init__(self):
        super(AuthManager, self).__init__(
            scheme_name="Session Token Auth",
            bearerFormat="Binary Data in Base64",
            description="Contains Session ID in Base64",
            auto_error=False,
        )

    async def __call__(self, request: Request) -> Optional[User]:
        await super().__call__(request)
        return SessionMiddleware.user(request)


def _add_auth_params(f: Any):
    """
    Adds a session parameter and related dependency into the function signature
    """
    s: inspect.Signature = inspect.signature(f)
    s = s.replace(
        parameters=[
            *s.parameters.values(),
            inspect.Parameter(
                AuthManager.KWARG,
                inspect.Parameter.KEYWORD_ONLY,
                default=Depends(AuthManager()),
            ),
        ]
    )
    f.__signature__ = s


def require_auth(*required_scopes: str):
    """
    This might require some explanations...

    The rationale is that since FastAPI does not (yet) detect the starlette
    Authentication middleware we will roll our own by dynamically adding
    parameters through modifying the apparent function signature.

    This seems to work (for the moment) at least.
    """

    def actual_auth_thingy(f):
        @wraps(f)
        async def check_auth(*args, **kwargs):
            user: User = kwargs.pop(AuthManager.KWARG)

            if not user.is_authenticated:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

            for scope in required_scopes:
                if scope not in user.scopes:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Unauthorized\n"
                               f'Required ({",".join(required_scopes)})\n'
                               f'Got ({",".join(user.scopes)})',
                    )

            return await f(*args, **kwargs)

        _add_auth_params(check_auth)

        return check_auth

    return actual_auth_thingy


__all__ = [
    "require_auth",
]
