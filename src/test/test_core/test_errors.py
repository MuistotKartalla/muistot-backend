"""
Basically just tests these output the right stuff
"""
import pytest
from muistoja.backend.models import ProjectInfo
from muistoja.errors import ApiError, ErrorResponse, Error
from muistoja.errors.helpers import db_error_handler, api_error_handler
from muistoja.errors.helpers import register_error_handlers, low_error_handler, modify_openapi
from muistoja.errors.helpers import validation_error_handler_2, validation_error_handler
from muistoja.errors.models import HTTPValidationError
from pydantic import ValidationError


@pytest.mark.anyio
async def test_api_error():
    r = await api_error_handler(None, ApiError(code=500, message="test"))
    r = Error.parse_raw(r.body)
    assert r.error.code == 500
    assert r.error.message == "test"


@pytest.mark.anyio
async def test_db_error():
    r = await db_error_handler(None, None)
    assert isinstance(r, ErrorResponse)
    assert Error.parse_raw(r.body).error.code == 503


@pytest.mark.anyio
async def test_db_integrity_error():
    from pymysql.err import IntegrityError
    r = await db_error_handler(None, IntegrityError())
    assert isinstance(r, ErrorResponse)
    assert Error.parse_raw(r.body).error.code == 409


@pytest.mark.anyio
async def test_validation_err_2():
    r = await validation_error_handler_2(None, None)
    r = Error.parse_raw(r.body)
    assert r.error.code == 500


@pytest.mark.anyio
async def test_validation_err():
    with pytest.raises(ValidationError) as e:
        ProjectInfo(lang="ggg", name="a")
    r = await validation_error_handler(None, e.value)
    r = HTTPValidationError.parse_raw(r.body)
    assert r.error.code == 422
    assert len(r.error.errors) == 1


@pytest.mark.anyio
async def test_validation_err_fail_parsing():
    r = await validation_error_handler(None, None)
    r = Error.parse_raw(r.body)
    assert r.error.code == 422
    assert "request" in r.error.message


@pytest.mark.parametrize("handler", [
    validation_error_handler,
    validation_error_handler_2,
    db_error_handler,
    api_error_handler,
    low_error_handler
])
def test_register(handler):
    from fastapi import FastAPI
    app = FastAPI()
    register_error_handlers(app)
    assert handler in app.exception_handlers.values()


@pytest.mark.anyio
async def test_low_err():
    from starlette.exceptions import HTTPException
    r = await low_error_handler(None, HTTPException(500))
    r = Error.parse_raw(r.body)
    assert r.error.code == 500


def test_openapi_modifier():
    class Mock:
        openapi_schema = None

        def openapi(self):
            return {"components": {"schemas": dict()}}

    app = Mock()
    modify_openapi(app)

    assert app.openapi_schema is not None
    assert len(app.openapi_schema["components"]["schemas"]) != 0  # Updates HTTPError


def test_api_error_splits_parts_on_newline():
    e = ApiError(code=400, message="a\nb")
    assert e.message == "a"
    assert e.details == ["b"]


def test_api_error_additional():
    e = ApiError(400, "a", "b", "c")
    assert e.message == "a"
    assert e.details == ["b", "c"]
