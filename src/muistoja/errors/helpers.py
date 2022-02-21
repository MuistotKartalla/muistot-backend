from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as LowHTTPException

from .models import *


def modify_openapi(app: FastAPI):
    try:
        from pydantic.schema import schema

        openapi = app.openapi()
        openapi["components"]["schemas"].update(
            schema([HTTPValidationError], ref_prefix="#/components/schemas/")[
                "definitions"
            ]
        )
        app.openapi_schema = openapi
    except Exception as e:
        from ..logging import log

        log.exception("Failed to setup OpenAPI", exc_info=e)


async def validation_error_handler(
        _: Request, exc: RequestValidationError
) -> JSONResponse:
    try:
        return JSONResponse(
            status_code=422,
            content=HTTPValidationError(
                error=ValidationErrorDetail(
                    code=422,
                    message="request validation error",
                    errors=jsonable_encoder(exc.errors()),
                )
            ).dict(),
        )
    except Exception as e:
        from ..logging import log

        log.exception("Failed request", exc_info=e)
        return ErrorResponse(ApiError(422, "request validation error"))


async def validation_error_handler_2(_: Request, exc: ValidationError) -> JSONResponse:
    from ..logging import log

    log.exception("Failed to parse database value", exc_info=exc)
    return ErrorResponse(
        ApiError(code=500, message="Could not parse value returned from database")
    )


async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return ErrorResponse(exc)


async def low_error_handler(_: Request, exc: LowHTTPException) -> ErrorResponse:
    return ErrorResponse(ApiError(exc.status_code, exc.detail))


async def db_error_handler(_: Request, exc) -> ErrorResponse:
    from ..logging import log

    log.exception("Database Error", exc_info=exc)
    return ErrorResponse(ApiError(code=503, message="Error in database Communication"))


def register_error_handlers(app: FastAPI):
    app.exception_handler(ApiError)(api_error_handler)
    app.exception_handler(RequestValidationError)(validation_error_handler)
    app.exception_handler(LowHTTPException)(low_error_handler)
    app.exception_handler(ValidationError)(validation_error_handler_2)

    try:
        from aiomysql import DatabaseError

        app.exception_handler(DatabaseError)(db_error_handler)
    except ImportError:
        pass


__all__ = ["register_error_handlers", "modify_openapi"]
