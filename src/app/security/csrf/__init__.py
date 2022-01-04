"""
Developed originally for Cookie Auth, but Header Auth was later selected.

This should work okay if cookies come into play.
"""
from typing import NoReturn

from fastapi import FastAPI, Request

from .hashes import verify, generate
from ...config import Config


def register_csrf_middleware(app: FastAPI) -> NoReturn:  # pragma: no cover
    if Config.security.csrf.enabled:
        @app.middleware("http")
        async def csrf_middleware(request: Request, call_next):
            from .csrf import check_request, set_csrf
            error = check_request(request)
            if error is None:
                resp = await call_next(request)
                if request.method == 'GET':
                    if request.user.is_authenticated:
                        set_csrf(resp, request.user.display_name)
                    else:
                        set_csrf(resp)
                return resp
            else:
                return error
