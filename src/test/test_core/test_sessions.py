import pytest
from headers import AUTHORIZATION
from muistoja.security import scopes
from muistoja.sessions.manager import Session
from muistoja.sessions.middleware import SessionManagerMiddleware
from starlette.authentication import AuthenticationError
from starlette.datastructures import MutableHeaders, State


class MockRequest:
    headers: MutableHeaders

    def __init__(self, auth):
        self.headers = MutableHeaders()
        self.headers[AUTHORIZATION] = auth
        self.state = State()


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
    assert e.value.args[0] == "Wrong Scheme"


@pytest.mark.anyio
async def test_bad_header():
    r = MockRequest("jwt ABSCD awdwawa")
    with pytest.raises(AuthenticationError) as e:
        await middleware.authenticate(r)
    assert e.value.args[0] == "Wrong Scheme"


@pytest.mark.anyio
async def test_no_header():
    r = MockRequest('')
    r.headers = MutableHeaders()
    a, u = await middleware.authenticate(r)
    assert type(r.state.manager) == MockManager
    assert not u.is_authenticated
