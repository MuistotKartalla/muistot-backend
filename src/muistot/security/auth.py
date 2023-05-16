"""
Supplies the functions needed to do the heavy lifting in authentication
"""
from functools import wraps
from typing import Any

from fastapi import Depends, status, Request

from .auth_helper import auth_helper
from .user import User

AUTH_HELPER = "__auth_helper__"
REQUEST_HELPER = "__request__"


async def _request_helper(r: Request):
    """Yeets the FastAPI request to the helper function since fastapi seems to allow request once per layer
    """
    yield r


def _add_request_param(f: Any):
    """
    Adds a request helper
    """
    import inspect

    s: inspect.Signature = inspect.signature(f)
    s = s.replace(
        parameters=[
            *s.parameters.values(),
            inspect.Parameter(
                REQUEST_HELPER,
                inspect.Parameter.KEYWORD_ONLY,
                default=Depends(_request_helper),
                annotation=None,
            ),
        ]
    )
    f.__signature__ = s


def _add_auth_params(f: Any, auth_scheme_choice):
    """
    Adds a session parameter and related dependency into the function signature
    """
    import inspect

    s: inspect.Signature = inspect.signature(f)
    s = s.replace(
        parameters=[
            *s.parameters.values(),
            inspect.Parameter(
                AUTH_HELPER,
                inspect.Parameter.KEYWORD_ONLY,
                default=Depends(auth_scheme_choice),
            ),
            inspect.Parameter(
                REQUEST_HELPER,
                inspect.Parameter.KEYWORD_ONLY,
                default=Depends(_request_helper),
                annotation=None,
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
            from fastapi import HTTPException

            kwargs.pop(AUTH_HELPER)
            r: Request = kwargs.pop(REQUEST_HELPER)
            user: User = r.user

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

        _add_auth_params(check_auth, auth_helper)

        return check_auth

    return actual_auth_thingy


__all__ = [
    "require_auth",
]
