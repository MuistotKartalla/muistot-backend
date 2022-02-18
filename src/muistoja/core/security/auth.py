"""
Supplies the functions needed to do the heavy lifting in authentication
"""
from typing import Any

from fastapi import FastAPI, Depends, status, Request

from .sessions import auth, add_session_manager
from .user import User

AUTH_HELPER = '__auth_helper__'
REQUEST_HELPER = '__request__'


def _add_session_params(f: Any, name: str, auth_scheme_choice):
    """
    Adds a session parameter and related dependency into the function signature
    """
    import inspect
    s: inspect.Signature = inspect.signature(f)
    s = s.replace(
        parameters=[
            *list(p for p in s.parameters.values() if p.name != name),
            inspect.Parameter(
                AUTH_HELPER,
                inspect.Parameter.KEYWORD_ONLY,
                default=Depends(auth_scheme_choice)
            ),
            inspect.Parameter(
                REQUEST_HELPER,
                inspect.Parameter.KEYWORD_ONLY,
                default=None,
                annotation=Request
            )
        ])
    f.__signature__ = s


def _check_func(f: Any):
    """
    Checks to see if the underlying function requests User parameter.

    If one is detected it is returned and will later be replaced with the proxy dependency value.
    """
    import inspect

    user_param = None
    for a in inspect.signature(f).parameters.values():
        if a.annotation == User:
            user_param = a.name
    return user_param


def register_auth(app: FastAPI):  # pragma: no cover
    """
    Adds the basic auth check to all endpoints
    """
    add_session_manager(app)


def require_auth(*required_scopes: str):
    """
    This might require some explanations...

    The rationale is that since FastAPI does not (yet) detect the starlette
    Authentication middleware we will roll our own by dynamically adding
    parameters through modifying the apparent function signature.

    This seems to work (for the moment) at least.
    """

    from functools import wraps

    def actual_auth_thingy(f):
        user_param = _check_func(f)

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
                        detail=f'Unauthorized\n'
                               f'Required ({",".join(required_scopes)})\n'
                               f'Got ({",".join(user.scopes)})'
                    )

            return await f(r, *args, **kwargs)

        _add_session_params(check_auth, user_param, auth)

        return check_auth

    return actual_auth_thingy


__all__ = [
    'register_auth',
    'require_auth',
]
