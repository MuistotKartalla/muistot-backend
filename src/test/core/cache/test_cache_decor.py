import pytest
from muistot.cache.decorator import Cache, _index_of, SHIM_KEY, CachesMeta


class Mock:
    class state:
        class cache:
            redis = None

    user = None


@pytest.fixture
def evicting():
    Cache._evicting = True
    yield
    Cache._evicting = False


@pytest.fixture(autouse=True)
def clear_instances():
    old = Cache._always_evict.copy()
    Cache._always_evict.clear()
    CachesMeta.instances.clear()
    yield
    CachesMeta.instances.clear()
    Cache._always_evict = old


def test_instance_same():
    a = Cache("memories")
    b = Cache("memories")
    assert a is b

    c = Cache("projects")
    d = Cache("projects")
    assert c is not a
    assert c is d


def test_index_of():
    async def func(a, b, c, /, g):
        pass

    assert _index_of("a", func) == 0
    assert _index_of("b", func) == 1
    assert _index_of("c", func) == 2
    assert _index_of("g", func) == 3

    with pytest.raises(ValueError):
        _index_of("d", func)


@pytest.mark.anyio
async def test_evicting_early_return_key(evicting):
    a = Cache("test")

    @a.key("c")
    async def assertion():
        return True

    # this will raise if it doesn't bypass
    assert await assertion(**{SHIM_KEY: Mock})


@pytest.mark.anyio
async def test_evicting_early_return_arg(evicting):
    a = Cache("test")

    @a.args("b")
    async def assertion(b=1):
        return True

    # this will raise if it doesn't bypass
    assert await assertion(**{SHIM_KEY: Mock})


@pytest.mark.anyio
async def test_exclude_early_return_kwarg():
    a = Cache("test")

    @a.args("b", exclude=lambda *args, **kwargs: kwargs["b"] == 1)
    async def assertion(*, b):
        return True

    # this will raise if it doesn't bypass
    assert await assertion(**{SHIM_KEY: Mock, "b": 1})


@pytest.mark.anyio
async def test_exclude_early_return_arg():
    a = Cache("test")

    @a.args("b", exclude=lambda *args, **kwargs: args[0] == 1)
    async def assertion(b, /):
        return True

    # this will raise if it doesn't bypass
    assert await assertion(1, **{SHIM_KEY: Mock})


@pytest.mark.anyio
async def test_evict_loop_only_first():
    # Evicting A should only evict B and eviction should not propagate
    a = Cache("a", evicts={"b"})
    b = Cache("b", evicts={"a", "c"})
    c = Cache("c", evicts={"b"})
    d = Cache("d", always_evict=True)

    evicted = [0]
    evicted_c = [0]
    evicted_d = [0]

    def eviction_proxy(*_):
        evicted[0] += 1

    def eviction_proxy_2(*_):
        evicted_c[0] += 1

    def eviction_proxy_3(*_):
        evicted_d[0] += 1

    a._evict = lambda *_: None
    b._evict = eviction_proxy
    c._evict = eviction_proxy_2
    d._evict = eviction_proxy_3

    @a.evict
    async def assertion():
        return True

    assert await assertion(**{SHIM_KEY: Mock})
    assert evicted[0] == 1
    assert evicted_c[0] == 0
    assert evicted_d[0] == 1  # Always evict


@pytest.mark.anyio
async def test_cache_operate_inject():
    from inspect import signature
    from fastapi import Depends
    a = Cache("test")

    assert a.Inject is Cache.Inject

    @a.use
    async def assertion(_: a.Operator = a.Inject):
        pass

    assert isinstance(signature(assertion).parameters["_"].default, type(Depends(a.operate)))


@pytest.mark.anyio
async def test_cache_operate_missing_inject():
    a = Cache("test")

    @a.use
    async def assertion(operator: a.Operator = None):
        assert operator is None
        return True

    # this will raise if it provides operator
    assert await assertion(**{SHIM_KEY: Mock})


@pytest.mark.anyio
async def test_cache_operate_yields():
    a = Cache("test")

    class Mock:
        class state:
            cache = None

    operator = [o async for o in a.operate(Mock)][0]
    assert isinstance(operator, a.Operator)


@pytest.mark.anyio
async def test_cache_operate_yields_none(evicting):
    a = Cache("test")

    class Mock:
        class state:
            cache = None

    operator = [o async for o in a.operate(Mock)][0]
    assert operator is None


def test_operator_set_adds_key():
    """Adds to set of all keys for clearing"""

    class MockRedis:
        ok = False

        def set(self, *_, **__):
            pass

        def sadd(self, *_, **__):
            MockRedis.ok = True

    class MockParent:
        store_prefix = "abc"

    op = Cache.Operator(MockParent, MockRedis())

    op.set('a', data=b'1234')

    assert MockRedis.ok


def test_operator_get_returns_value():
    """Just a sanity check for returning raw value"""
    flag = object()

    class MockRedis:
        ok = False

        def get(self, *_, **__):
            return flag

    class MockParent:
        store_prefix = "abc"

    op = Cache.Operator(MockParent, MockRedis())

    assert op.get('a') is flag


@pytest.mark.anyio
async def test_cache_evict_only_once():
    a = Cache("a", evicts={"b"})
    b = Cache("b", always_evict=True)

    assert b.name == "b"

    evict_count = [0]

    def proxy(*_, **__):
        Cache._evicted.add(b.name)
        evict_count[0] += 1

    a._evict = lambda *_, **__: None
    b._evict = proxy

    @a.evict
    async def assertion():
        return True

    assert await assertion(**{SHIM_KEY: Mock})
    assert evict_count[0] == 1  # fails if b was evicted twice (From a and always)
