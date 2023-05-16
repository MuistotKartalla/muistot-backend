from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as LowHTTPException

from .models import *
from ..database import OperationalError, IntegrityError, InterfaceError, DatabaseError
from ..logging import log


async def request_validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
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
        log.exception("Failed request", exc_info=e)
        return ErrorResponse(ApiError(422, "request validation error"))


async def validation_error_handler_2(_: Request, exc: ValidationError) -> JSONResponse:
    log.exception("Failed to parse database value", exc_info=exc)
    return ErrorResponse(
        ApiError(code=500, message="Could not parse value returned from database")
    )


async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return ErrorResponse(exc)


async def low_error_handler(_: Request, exc: LowHTTPException) -> ErrorResponse:
    return ErrorResponse(ApiError(exc.status_code, exc.detail))


async def db_error_handler(_: Request, exc) -> ErrorResponse:
    if isinstance(exc, IntegrityError):
        log.warning("Integrity Violation", exc_info=exc)
        return ErrorResponse(ApiError(code=409, message="Integrity Violation"))
    elif isinstance(exc, (InterfaceError, OperationalError)):
        if exc.__cause__ is None or type(exc.__cause__) != TimeoutError:
            log.warning("Database Communication Error", exc_info=exc)
        else:
            log.warning("Database Connections Exhausted")
        return ErrorResponse(ApiError(code=503, message="Lost Connection to Database"))
    else:
        log.warning("Unknown Database Error", exc_info=exc)
        return ErrorResponse(ApiError(code=500, message="Error in database Communication"))


exception_handlers = {
    ApiError: api_error_handler,
    RequestValidationError: request_validation_error_handler,
    LowHTTPException: low_error_handler,
    ValidationError: validation_error_handler_2,
    DatabaseError: db_error_handler,
}
