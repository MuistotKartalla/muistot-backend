from typing import NoReturn, Optional, List

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from .hashes import verify, generate
from ..config import Config

ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH"}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

HEADER = "X-Muistot-State"
LIFETIME = Config.security.csrf_lifetime


def respond(code: int, message: str, details: List[str] = None) -> JSONResponse:
    response = JSONResponse(content={
        "error": {
            "message": message,
            **({"details": details} if details is not None else {})
        }
    })
    response.status_code = code
    return response


RESPONSES = {
    'bad-method': respond(405, "method not allowed on this domain"),
    'bad-value': respond(
        400,
        "request validation failed",
        details=["bad value"]
    ),
    'bad-token': respond(
        400,
        "request validation failed",
        details=["bad token"]
    ),
    'bad-length': respond(
        400,
        "request validation failed",
        details=["bad token"]
    ),
    'bad-encoding': respond(
        400,
        "request validation failed",
        details=["bad token"]
    ),
    'missing-value': respond(
        400,
        "request validation failed",
        details=["missing value"]
    ),
    'unexpected': respond(
        400,
        "request validation failed",
        details=["unexpected result"]
    ),
    'expired': respond(
        400,
        "request validation failed",
        details=["expired"]
    ),
    'mismatch': respond(
        400,
        "request validation failed",
        details=["mismatch"]
    )
}


def set_csrf(response: Response) -> NoReturn:
    token = generate(LIFETIME)
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
                out = RESPONSES['missing-value']
            except ValueError as e:
                out = RESPONSES[e.args[0]]
            except Exception as e:  # pragma: no cover
                import logging
                logging.getLogger("uvicorn.error").warning("Exception", exc_info=e)
                out = RESPONSES['unexpected']
    else:
        out = RESPONSES['bad-method']
    return out


def register_csrf_middleware(app: FastAPI) -> NoReturn:  # pragma: no cover
    @app.middleware("http")
    async def csrf_middleware(request: Request, call_next):
        error = check_request(request)
        if error is None:
            resp = await call_next(request)
            if request.method == 'GET':
                set_csrf(resp)
            return resp
        else:
            return error
