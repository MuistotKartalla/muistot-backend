import json

import pytest
from muistot.sessions.helpers import register_session_manager
from muistot.sessions.manager import SessionManager, Session, USER_PREFIX, TOKEN_PREFIX, decode, encode


@pytest.fixture
def mgr() -> SessionManager:
    class State:
        SessionManager = None

    class App:
        state = State

        def add_middleware(self, *_, **__):
            pass

    register_session_manager(App)
    manager: SessionManager = App.state.SessionManager
    manager.connect()
    yield manager
    manager.disconnect()
    del manager


def test_extend_nonexistent_noop(mgr):
    mgr.extend("not-existing:dwadwawd")
    mgr.extend(b"not-existing:dwadwawd")


def test_start_end_session(mgr):
    token = mgr.start_session(Session(user="test", data=dict()))

    mgr.end_session(token)

    assert not mgr.redis.exists(TOKEN_PREFIX + decode(token))
    assert len(mgr.redis.smembers(USER_PREFIX + "test")) == 0
    assert len(mgr.get_sessions("test")) == 0


def test_cull_old(mgr):
    mgr.redis.sadd(USER_PREFIX + "tc", b"1234")
    mgr.clear_stale("tc")
    assert len(mgr.redis.smembers(USER_PREFIX + "tc")) == 0


def test_cull_on_load_all(mgr):
    mgr.redis.sadd(USER_PREFIX + "tc2", b"1234")
    assert len(mgr.get_sessions("tc2")) == 0
    assert len(mgr.redis.smembers(USER_PREFIX + "test_cull_2")) == 0


def test_cull_and_get_on_load_all(mgr):
    mgr.redis.sadd(USER_PREFIX + "tc3", b"1234")
    mgr.redis.sadd(USER_PREFIX + "tc3", TOKEN_PREFIX + b"12345")
    mgr.redis.set(TOKEN_PREFIX + b"12345", json.dumps(dict(user="tc3", data=dict())))

    sessions = mgr.get_sessions("tc3")

    assert len(sessions) == 1
    assert sessions[0].user == "tc3" and len(sessions[0].data) == 0
    assert len(mgr.redis.smembers(USER_PREFIX + "tc3")) == 1


def test_clear_all_user_sessions(mgr):
    mgr.redis.sadd(USER_PREFIX + "ca", b"abc")
    mgr.redis.sadd(USER_PREFIX + "ca", TOKEN_PREFIX + b"def")
    mgr.redis.set(TOKEN_PREFIX + b"def", json.dumps(dict(user="ca", data=dict())))

    mgr.clear_sessions("ca")

    assert not mgr.redis.exists(TOKEN_PREFIX + b"abc")
    assert not mgr.redis.exists(TOKEN_PREFIX + b"def")
    assert len(mgr.redis.smembers(USER_PREFIX + "ca")) == 0


def test_clear_all_sessions(mgr):
    mgr.redis.sadd(USER_PREFIX + "a", b"a")
    mgr.redis.sadd(USER_PREFIX + "b", TOKEN_PREFIX + b"b")
    mgr.redis.set(TOKEN_PREFIX + b"b", json.dumps(dict(user="b", data=dict())))

    mgr.clear_all_sessions()

    assert not mgr.redis.exists(TOKEN_PREFIX + b"a")
    assert not mgr.redis.exists(TOKEN_PREFIX + b"b")
    assert len(mgr.redis.smembers(USER_PREFIX + "a")) == 0
    assert len(mgr.redis.smembers(USER_PREFIX + "b")) == 0


def test_get_session(mgr):
    mgr.redis.sadd(USER_PREFIX + "gs", TOKEN_PREFIX + b"gs")
    mgr.redis.set(TOKEN_PREFIX + b"gs", json.dumps(dict(user="test", data=dict(success=True))))

    s = mgr.get_session(encode(TOKEN_PREFIX + b"gs"))
    assert s.user == "test"
    assert s.data["success"]


def test_start_get_session(mgr):
    t = mgr.start_session(Session(user="test", data=dict(success=True)))
    s = mgr.get_session(t)
    assert s.user == "test"
    assert s.data["success"]


def test_get_bad_session(mgr):
    with pytest.raises(ValueError) as e:
        mgr.get_session(encode(b"will-not-exist"))
    assert "invalid session" in str(e.value).lower()
