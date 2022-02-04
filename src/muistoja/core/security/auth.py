"""
Supplies the functions needed to do the heavy lifting in authentication
"""
from typing import Any

from fastapi import FastAPI, Depends, status, Request

from .sessions import auth, add_session_manager
from .user import User


def _add_session_param(f: Any, name: str, auth_scheme_choice):
    """
    Adds a session parameter and related dependency into the function signature
    """
    import inspect
    s: inspect.Signature = inspect.signature(f)
    s = s.replace(
        parameters=[
            *list(p for p in s.parameters.values() if p.name != name),
            inspect.Parameter(
                '__auth_helper__',
                inspect.Parameter.KEYWORD_ONLY,
                default=Depends(auth_scheme_choice),
                annotation=User
            )])
    f.__signature__ = s


def _check_func(f: Any):
    """
    Checks to see if the underlying function requests User parameter.

    If one is detected it is returned and will later be replaced with the proxy dependency value.
    """
    import inspect
    # Check that the scope is actually probably maybe used
    if next(iter(inspect.signature(f).parameters.values())).annotation != Request:
        assert False, f'Request (r) parameter is not found for function {f.__name__}. Should be first.'

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

    There are two types of auth available and the lighter one is used if only
    the login status needs to be checked.
    """

    from functools import wraps

    def actual_auth_thingy(f):
        user_param = _check_func(f)

        @wraps(f)
        async def check_auth(r: Request, *args, **kwargs):
            from fastapi import HTTPException
            try:
                kwargs.pop('__auth_helper__')
                user: User = r.user
                for scope in required_scopes:
                    if scope not in user.scopes:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f'Unauthorized\n'
                                   f'Required ({",".join(required_scopes)})\n'
                                   f'Got ({",".join(user.scopes)})'
                        )
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

        _add_session_param(check_auth, user_param, auth)

        return check_auth

    return actual_auth_thingy


__all__ = [
    'register_auth',
    'require_auth',
]
