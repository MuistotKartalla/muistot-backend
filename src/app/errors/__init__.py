from typing import Optional, List

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ApiError(Exception):

    def __init__(self, code: int, message: str, *additional_details: str):
        self.code = code
        parts = message.splitlines(keepends=False)
        if len(parts) > 1:
            self.message = parts[0]
            self.details = parts[1:] + list(additional_details)
        else:
            self.message = message
            self.details = list(additional_details)


class ErrorResponse(JSONResponse):
    def __init__(self, error: ApiError):
        super(ErrorResponse, self).__init__(
            status_code=error.code,
            content=Error(error=ErrorDetail(
                code=error.code,
                message=error.message,
                details=(error.details if len(error.details) > 0 else None)
            )).dict(exclude_none=True)
        )


class ErrorDetail(BaseModel):
    code: int
    message: str
    details: Optional[List[str]]


class Error(BaseModel):
    error: ErrorDetail


class ValidationErrorLocation(BaseModel):
    loc: List[str]
    msg: str
    type: str


class ValidationErrorDetail(BaseModel):
    code: int
    message: str
    errors: List[ValidationErrorLocation]


class HTTPValidationError(BaseModel):
    error: ValidationErrorDetail


def modify_openapi(app: FastAPI):
    try:
        from pydantic.schema import schema
        openapi = app.openapi()
        openapi["components"]["schemas"].update(schema(
            [HTTPValidationError],
            ref_prefix="#/components/schemas/"
        )["definitions"])
        app.openapi_schema = openapi
    except Exception as e:
        from ..logging import log
        log.exception('Failed to setup OpenAPI', exc_info=e)


def register_error_handlers(app: FastAPI):
    @app.exception_handler(ApiError)
    async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
        return ErrorResponse(exc)

    @app.exception_handler(RequestValidationError)
    async def api_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        try:
            return JSONResponse(status_code=422, content=HTTPValidationError(error=ValidationErrorDetail(
                code=422,
                message="request validation error",
                errors=jsonable_encoder(exc.errors())
            )))
        except Exception as e:
            from ..logging import log
            log.exception('Failed request', exc_info=e)
            return ErrorResponse(ApiError(422, "request validation error"))

    try:
        from starlette.exceptions import HTTPException as LowHTTPException

        @app.exception_handler(LowHTTPException)
        async def low_error_handler(_: Request, exc: LowHTTPException) -> ErrorResponse:
            return ErrorResponse(ApiError(exc.status_code, exc.detail))
    except ImportError:
        pass


__all__ = [
    'ApiError',
    'ErrorResponse',
    'register_error_handlers',
    'modify_openapi',
    'Error'
]
