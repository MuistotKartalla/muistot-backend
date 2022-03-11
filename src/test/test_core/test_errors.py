"""
Basically just tests these output the right stuff
"""
import pytest
from muistoja.backend.models import ProjectInfo
from muistoja.errors import ApiError, ErrorResponse, Error
from muistoja.errors.helpers import db_error_handler, api_error_handler
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
    assert Error.parse_raw(r.body)


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
async def test_validation_err():
    r = await validation_error_handler(None, None)
    r = Error.parse_raw(r.body)
    assert r.error.code == 422
    assert "request" in r.error.message
