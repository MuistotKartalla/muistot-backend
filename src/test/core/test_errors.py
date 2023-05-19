"""
Basically just tests these output the right stuff
"""
import pytest
from pydantic import ValidationError

from muistot.backend.models import ProjectInfo
from muistot.database import OperationalError, IntegrityError, InterfaceError
from muistot.errors import ApiError, ErrorResponse, Error, exception_handlers, modify_openapi
from muistot.errors.handlers import (
    db_error_handler,
    api_error_handler,
    low_error_handler,
    validation_error_handler_2,
    request_validation_error_handler,
)
from muistot.errors.models import HTTPValidationError


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
    assert Error.parse_raw(r.body).error.code == 500


@pytest.mark.anyio
async def test_db_integrity_error():
    r = await db_error_handler(None, IntegrityError())
    assert isinstance(r, ErrorResponse)
    assert Error.parse_raw(r.body).error.code == 409


@pytest.mark.anyio
async def test_db_interface_error():
    r = await db_error_handler(None, InterfaceError())
    assert isinstance(r, ErrorResponse)
    assert Error.parse_raw(r.body).error.code == 503


@pytest.mark.anyio
async def test_db_operational_error():
    r = await db_error_handler(None, OperationalError())
    assert isinstance(r, ErrorResponse)
    assert Error.parse_raw(r.body).error.code == 503


@pytest.mark.anyio
async def test_validation_err_2():
    r = await validation_error_handler_2(None, None)
    r = Error.parse_raw(r.body)
    assert r.error.code == 500


@pytest.mark.anyio
async def test_validation_err():
    with pytest.raises(ValidationError) as e:
        ProjectInfo(lang="ggg", name="a")
    r = await request_validation_error_handler(None, e.value)
    r = HTTPValidationError.parse_raw(r.body)
    assert r.error.code == 422
    assert len(r.error.errors) == 1


@pytest.mark.anyio
async def test_validation_err_fail_parsing():
    r = await request_validation_error_handler(None, None)
    r = Error.parse_raw(r.body)
    assert r.error.code == 422
    assert "request" in r.error.message


@pytest.mark.parametrize("handler", [
    request_validation_error_handler,
    validation_error_handler_2,
    db_error_handler,
    api_error_handler,
    low_error_handler
])
def test_register(handler):
    from fastapi import FastAPI
    app = FastAPI(exception_handlers=exception_handlers)
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
        root_path = "/api"
        servers = list()

        def openapi(self):
            return {"components": {"schemas": dict()}}

    app = Mock()
    modify_openapi(app)

    assert len(app.servers) != 0
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


@pytest.mark.anyio
async def test_db_operational_error_2():
    e = OperationalError()
    e.__cause__ = TimeoutError()
    r = await db_error_handler(None, e)
    assert isinstance(r, ErrorResponse)
    err = Error.parse_raw(r.body).error
    assert err.code == 503
    assert "Lost" in err.message
