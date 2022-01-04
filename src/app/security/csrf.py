from typing import NoReturn, Optional, List

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from .hashes import verify, generate
from ..config import Config

ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH"}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

HEADER = "X-Muistot-State"
LIFETIME = Config.security.csrf_lifetime


def respond(code: int = 400, message: str = "request validation failed", details: List[str] = None) -> JSONResponse:
    return JSONResponse(content={
        "error": {
            "message": message,
            **({"details": details} if details is not None else {})
        }
    }, status_code=code)


def set_csrf(response: Response, payload: Optional[str] = None) -> NoReturn:
    token = generate(LIFETIME, None if payload is None else payload.encode('utf-8'))
    response.headers[HEADER] = token


def check_request(request: Request) -> Optional[JSONResponse]:
    """
    Validates CSRF prevention cookie.
    Additionally checks request for method and rejects unused ones.

    :param request: Incoming request from FastAPI
    :return:        JSONResponse on failure to verify
    """
    out = None
    if request.method in ALLOWED_METHODS:
        if request.method not in SAFE_METHODS:
            try:
                token = request.headers[HEADER]
                verify(token)
            except KeyError:
                out = respond(details=['missing-value'])
            except ValueError as e:
                try:
                    out = respond(details=[e.args[0]])
                except IndexError:  # pragma: no cover
                    out = respond(details=["unexpected state"])
            except Exception as e:  # pragma: no cover
                import logging
                logging.getLogger("uvicorn.error").warning("Exception", exc_info=e)
                out = respond(details=['unexpected'])
    else:
        out = respond(405, "method not allowed on this domain", ['bad-method'])
    return out


def register_csrf_middleware(app: FastAPI) -> NoReturn:  # pragma: no cover
    @app.middleware("http")
    async def csrf_middleware(request: Request, call_next):
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
