from typing import Optional, List

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
            content=Error(
                error=ErrorDetail(
                    code=error.code,
                    message=error.message,
                    details=(error.details if len(error.details) > 0 else None),
                )
            ).dict(exclude_none=True),
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
    """
    This is a serialized Pydantic validation error.

    Contains detailed information on where validation went wrong.
    Directly from Pydantic.
    """

    error: ValidationErrorDetail

    class Config:
        schema_extra = {
            "example": {
                "error": {
                    "code": 422,
                    "message": "request validation error",
                    "errors": [
                        {
                            "loc": ["this is from", "pydantic"],
                            "msg": "a value was wrong somewhere",
                            "type": "pydantic error type",
                        }
                    ],
                }
            }
        }


__all__ = [
    "ApiError",
    "ErrorResponse",
    "ValidationErrorDetail",
    "HTTPValidationError",
    "Error",
]
