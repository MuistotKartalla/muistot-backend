import pytest
from muistot.security.auth import _add_auth_params, require_auth, AUTH_HELPER, REQUEST_HELPER, _add_request_param, \
    disallow_auth
from muistot.security.auth_helper import auth_helper
from muistot.security.password import hash_password, check_password


def test_manager_add():
    from muistot.sessions import register_session_manager
    from muistot.sessions.middleware import SessionManagerMiddleware
    from starlette.middleware.authentication import AuthenticationMiddleware

    class State:
        SessionManager = None

    class Mock:
        state = State

        @staticmethod
        def add_middleware(middleware, **opts):
            assert middleware == AuthenticationMiddleware
            assert type(opts["backend"]) == SessionManagerMiddleware
            assert "on_error" in opts

    register_session_manager(Mock)
    assert State.SessionManager is not None


@pytest.mark.anyio
async def test_helper_extracts_user():
    class Mock:
        user = True

    assert await auth_helper(Mock())  # FastAPI without generator


def test_hashing_is_ok():
    import string
    import random
    s = ''.join(random.choice(string.printable) for _ in range(0, random.randint(4, 64)))
    assert check_password(password_hash=hash_password(password=s), password=s)


def test_empty_not_equal():
    import string
    import random
    s = ''.join(random.choice(string.printable) for _ in range(0, random.randint(4, 64)))
    assert not check_password(password_hash=b"", password=s)
    assert not check_password(password_hash=hash_password(password=s), password="None")


def test_none_raises():
    with pytest.raises(TypeError):
        hash_password(password=None)


def test_check_fails_on_none():
    assert not check_password(password_hash=None, password="a")
    assert not check_password(password_hash=hash_password(password="a"), password=None)


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
    from fastapi import HTTPException

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


@pytest.mark.anyio
async def test_disallow_auth():
    from fastapi import HTTPException
    class MockU:
        is_authenticated = True

    class Mock:
        user = MockU

    @disallow_auth
    async def disallow():
        pass

    with pytest.raises(HTTPException) as e:
        await disallow(**{REQUEST_HELPER: Mock})

    assert e.value.status_code == 403
