from typing import NoReturn, Optional, List

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from .hashes import verify, generate
from ...config import Config

ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH"}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

HEADER = "X-Muistot-State"
LIFETIME = Config.security.csrf.lifetime


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
    Validates CSRF prevention.
    Additionally checks request for method and rejects unused ones.

    :param request: Incoming request from FastAPI
    :return:        JSONResponse on failure to verify
    """
    out = None
    if request.method in ALLOWED_METHODS:
        if request.method not in SAFE_METHODS:
            try:
                token = request.headers[HEADER]
                data = verify(token)
                if request.user.is_authenticated:
                    if data != request.user.display_name.encode('utf-8'):
                        out = respond(details=['bad-payload'])
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
