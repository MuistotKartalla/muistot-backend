import pytest
from muistot.cache.decorator import Cache, _index_of, SHIM_KEY, CachesMeta


class Mock:
    class state:
        class cache:
            redis = None

    user = None


@pytest.fixture
def evicting():
    Cache.evicting = True
    yield
    Cache.evicting = False


@pytest.fixture(autouse=True)
def clear_instances():
    CachesMeta.instances.clear()
    yield
    CachesMeta.instances.clear()


def test_instance_same():
    a = Cache("memories")
    b = Cache("memories")
    assert a is b

    c = Cache("projects")
    assert c is not a


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

    evicted = [0]
    evicted_c = [0]

    def eviction_proxy(*_):
        evicted[0] += 1

    def eviction_proxy_2(*_):
        evicted_c[0] += 1

    a._evict = lambda *_: None
    b._evict = eviction_proxy
    c._evict = eviction_proxy_2

    @a.evict
    async def assertion():
        return True

    assert await assertion(**{SHIM_KEY: Mock})
    assert evicted[0] == 1
    assert evicted_c[0] == 0
