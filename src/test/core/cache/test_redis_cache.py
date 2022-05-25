import time

import pytest
from muistot.cache import register_redis_cache as use_redis_cache


@pytest.fixture
def redis():
    class State:
        FastStorage = None

    class App:
        state = State

        @staticmethod
        def middleware(*_):
            return lambda f: None

        @staticmethod
        def on_event(*_):
            return lambda f: None

    use_redis_cache(App)
    i = App.state.FastStorage
    assert i is not None
    i.connect()
    yield i
    i.disconnect()
    del i


def test_get_set_custom(redis):
    redis.set("a", "", ttl=2)
    time.sleep(3)
    assert redis.get("a") is None


def test_get_set_custom_with_prefix(redis):
    redis.set("a", "c", prefix="b")
    assert redis.get("a") is None
    assert redis.get("a", prefix="b") == "c".encode("utf-8")


def test_set_delete_custom(redis):
    redis.set("a", "c", prefix="b")
    redis.delete("a")
    assert redis.get("a", prefix="b") == "c".encode("utf-8")
    redis.delete("a", prefix="b")
    assert redis.get("a", prefix="b") is None


def test_connect_on_startup():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    use_redis_cache(app)
    i = app.state.FastStorage
    with TestClient(app):
        assert i.redis is not None
    assert i.redis is None


def test_disconnect_without_connect_ok():
    from fastapi import FastAPI
    app = FastAPI()
    use_redis_cache(app)
    i = app.state.FastStorage
    assert i.redis is None
    i.disconnect()
    assert i.redis is None
