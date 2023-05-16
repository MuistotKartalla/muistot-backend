import pytest
from fastapi import HTTPException

from muistot.security.auth import (
    _add_auth_params,
    require_auth,
    AUTH_HELPER,
    REQUEST_HELPER,
    _add_request_param,
)
from muistot.security.auth_helper import auth_helper


@pytest.mark.anyio
async def test_helper_extracts_user():
    class Mock:
        user = True

    assert await auth_helper(Mock())  # FastAPI without generator


def test_adds_params_to_signature():
    def mock():
        return True

    _add_auth_params(mock, None)

    import inspect
    s = inspect.signature(mock)
    assert REQUEST_HELPER in s.parameters.keys()
    assert AUTH_HELPER in s.parameters.keys()


@pytest.mark.anyio
async def test_add_auth():
    class MockU:
        is_authenticated = False
        scopes = set()

    class MockR:
        user = MockU

    async def mock():
        return True

    f = require_auth("A")(mock)
    args = {AUTH_HELPER: None, REQUEST_HELPER: MockR}

    # Test Not Authenticated
    with pytest.raises(HTTPException) as e:
        await f(**args)
    assert e.value.status_code == 401

    # Test No Scope
    MockU.is_authenticated = True
    with pytest.raises(HTTPException) as e:
        await f(**args)
    assert e.value.status_code == 403

    # Test Success
    MockU.scopes.add("A")
    assert await f(**args)


def test_adds_request_param_to_signature():
    def mock():
        return True

    _add_request_param(mock)

    import inspect
    s = inspect.signature(mock)
    assert REQUEST_HELPER in s.parameters.keys()
