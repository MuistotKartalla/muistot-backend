import pytest
from headers import AUTHORIZATION
from muistot.security import scopes
from muistot.sessions.helpers import on_error
from muistot.sessions.manager import Session, decode, encode
from muistot.sessions.middleware import SessionManagerMiddleware
from starlette.authentication import AuthenticationError
from starlette.datastructures import MutableHeaders, State


class MockRequest:
    headers: MutableHeaders

    def __init__(self, auth):
        self.headers = MutableHeaders()
        self.headers[AUTHORIZATION] = auth
        self.state = State()
        self.scope = dict()


class MockManager:
    def __init__(self):
        pass

    def connect(self):
        pass

    def disconnect(self):
        pass

    def extend(self, value):
        pass

    def get_session(self, token):
        if token == "raise":
            raise ValueError()
        return Session(
            user="mock",
            data=dict(
                scopes=[scopes.AUTHENTICATED, scopes.ADMIN], projects=["mock-project"]
            ),
        )

    def start_session(self, session):
        pass

    def end_session(self, token: str):
        pass

    def clear_sessions(self, user: str):
        pass

    def clear_all_sessions(self):
        pass


middleware = SessionManagerMiddleware(MockManager())


@pytest.mark.anyio
async def test_simple_request():
    r = MockRequest("jwt ABSCD")
    with pytest.raises(AuthenticationError) as e:
        await middleware.authenticate(r)
    assert e.value.__cause__.args[0] == "Wrong Scheme"


@pytest.mark.anyio
async def test_bad_header():
    r = MockRequest("jwt ABSCD awdwawa")
    with pytest.raises(AuthenticationError) as e:
        await middleware.authenticate(r)
    assert e.value.__cause__.args[0] == "Wrong Scheme"


@pytest.mark.anyio
async def test_no_header():
    r = MockRequest("")
    r.headers = MutableHeaders()
    a, u = await middleware.authenticate(r)
    assert type(r.state.manager) == MockManager
    assert not u.is_authenticated


@pytest.mark.anyio
async def test_simple_session():
    r = MockRequest("Bearer a")
    a, u = await middleware.authenticate(r)
    assert type(r.state.manager) == MockManager
    assert u.is_authenticated
    assert u.username == "mock"
    assert list(u.admin_projects) == ["mock-project"]
    assert scopes.AUTHENTICATED in u.scopes
    assert scopes.ADMIN in u.scopes


@pytest.mark.anyio
async def test_invalid_session():
    r = MockRequest("bearer raise")
    with pytest.raises(AuthenticationError):
        await middleware.authenticate(r)


def test_on_error_handles_no_args():
    r = on_error(None, RuntimeError())
    assert r.status_code == 401


def test_encode_correctness():
    import hashlib
    a = b"abcd"
    assert decode(encode(a)) == hashlib.sha256(a).digest()


def test_decode_invalid_base64():
    a = "/+"
    with pytest.raises(ValueError):
        assert decode(a)


def test_decode_not_ascii():
    a = "öä"
    with pytest.raises(ValueError):
        assert decode(a)


@pytest.mark.anyio
async def test_manager_decode_data_correctness_missing():
    class MockManager2(MockManager):

        def get_session(self, token):
            if token == "raise":
                raise ValueError()
            return Session(
                user="a",
                data=dict(
                    scopes=[],
                    projects=[]
                ),
            )

    middleware2 = SessionManagerMiddleware(MockManager2())

    class MockManager3(MockManager):

        def get_session(self, token):
            if token == "raise":
                raise ValueError()
            return Session(
                user="a",
                data=dict(
                ),
            )

    middleware3 = SessionManagerMiddleware(MockManager3())

    r = MockRequest("Bearer a")
    a2, u2 = await middleware2.authenticate(r)
    a3, u3 = await middleware3.authenticate(r)

    assert u2.admin_projects == u3.admin_projects
    assert u2.scopes == u3.scopes
