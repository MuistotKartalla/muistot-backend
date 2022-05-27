import collections
import contextlib
import functools
import hashlib
import inspect
import itertools
import threading
import typing

import redis
from fastapi import Request, Depends
from fastapi.params import Depends as DependsParam
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel

from .redis import FastStorage
from ..config import Config
from ..database import DatabaseDependency
from ..security import User


class LazyDelegator:
    __slots__ = ['dep', 'wrapped', 'stack']

    wrapped: typing.Any
    stack: contextlib.AsyncExitStack
    dep: typing.Optional[DatabaseDependency]

    def __init__(self, wrapped, stack):
        self.wrapped = wrapped
        self.stack = stack
        self.dep = None

    def __getattr__(self, item: str):
        """
        Delegate Calls with Lazy Initialization

        This will fail if the first attribute called is not async
        """
        if self.dep is None:
            async def proxy_call(*args, **kwargs):
                self.dep = await self.stack.enter_async_context(self.wrapped())
                return await getattr(self.dep, item)(*args, **kwargs)

            return proxy_call
        else:
            return getattr(self.dep, item)


class DelayedDependency:
    """
    This is used to delay database dependency gets to not run out of connections
    """
    stack: contextlib.AsyncExitStack
    wrapped: typing.Any

    def __init__(self, dependency: DatabaseDependency):
        self.wrapped = contextlib.asynccontextmanager(dependency)

    async def __call__(self):
        """FastAPI"""
        async with contextlib.AsyncExitStack() as stack:
            yield LazyDelegator(self.wrapped, stack)


STORAGE = "entity-cache:{}:"
SHIM_KEY = "__cache_shim__"
TTL = Config.cache.cache_ttl

FUNC_TYPE = typing.Callable[..., typing.Awaitable[BaseModel]]


def shash(data: typing.Iterable[typing.Any]):
    d = hashlib.md5()
    for a in data:
        d.update(str(a).encode("utf-8"))
    return d.digest()


async def _get_request(r: Request):
    yield r


def _add_shim(f: FUNC_TYPE, replace_deps: bool = False) -> FUNC_TYPE:
    cache_shim = SHIM_KEY

    s = inspect.signature(f)

    params = list()
    if replace_deps:
        """
        Replaces Dependency With a mock one that will later be called if needed
        """
        for v in s.parameters.values():
            if type(v.default) == DependsParam and type(v.default.dependency) == DatabaseDependency:
                v = v.replace(default=Depends(DelayedDependency(v.default.dependency), use_cache=False))
            params.append(v)
    else:
        params.extend(s.parameters.values())

    f.__signature__ = s.replace(
        parameters=[
            *params,
            inspect.Parameter(
                name=cache_shim,
                default=Depends(_get_request),
                kind=inspect.Parameter.KEYWORD_ONLY
            )
        ]
    )

    return f


def _pop(kwargs: typing.Dict[str, typing.Any]) -> typing.Tuple[FastStorage, User]:
    r: Request = kwargs.pop(SHIM_KEY)
    return r.state.cache, r.user


def _index_of(arg: str, f: FUNC_TYPE) -> int:
    s = inspect.signature(f)
    found_index: int = -1
    for idx, p in enumerate(s.parameters.values()):
        if p.name == arg:
            found_index = idx
            break
    if found_index != -1:
        return found_index
    else:
        raise ValueError("No Arg Found")


class CachesMeta(type):
    instances = dict()
    lock = threading.Lock()

    def __call__(cls, _type: str, **kwargs) -> 'Cache':
        o = CachesMeta.instances.get(_type, None)
        if o is None:
            with CachesMeta.lock:
                o = CachesMeta.instances.get(_type, None)
                if o is None:
                    o = super(CachesMeta, cls).__call__(_type, **kwargs)
                    CachesMeta.instances[_type] = o
        return o


class Cache(metaclass=CachesMeta):
    _evicting = False
    _always_evict = collections.deque()
    _evicted = set()

    Operator: 'CacheOperator'
    """
    Typehint Access for Operator
    """

    Inject: typing.Any = object()
    """
    Inject marker for Cache.use decorator
    """

    def __init__(self, prefix: str, *, evicts: typing.Set[str] = None, always_evict: bool = False):
        self.name = prefix
        self.store_prefix = STORAGE.format(prefix)
        self.evicts = list(evicts) if evicts is not None else list()
        # Locking
        self.lock = threading.Lock()
        if always_evict:
            Cache._always_evict.append(prefix)

    async def _get_from_cache(
            self,
            r: redis.Redis,
            f: FUNC_TYPE,
            args: typing.Sequence[typing.Any],
            kwargs: typing.Dict[str, typing.Any],
            prefix: str,
            _type: str,
            *keys,
    ) -> typing.Union[BaseModel, Response]:
        key = f"{prefix}{_type}:".encode("ascii") + shash(keys)
        data = r.get(key)
        if data is None:
            with self.lock:
                data = r.get(key)
                if data is None:
                    response_entity: BaseModel = await f(*args, **kwargs)
                    r.sadd(f"{prefix}all".encode("ascii"), key)
                    r.set(key, response_entity.json(), ex=TTL)
                    return response_entity
        return Response(status_code=200, content=data, media_type=JSONResponse.media_type)

    def key(self, key: str):

        def cache_decorator(f: FUNC_TYPE) -> FUNC_TYPE:
            @functools.wraps(f)
            async def wrapper(*args, **kwargs):
                c, u = _pop(kwargs)
                if Cache._evicting:
                    return await f(*args, **kwargs)
                return await self._get_from_cache(
                    c.redis,
                    f,
                    args,
                    kwargs,
                    self.store_prefix,
                    "key",
                    f.__name__,
                    *u.scopes,
                    key
                )

            return _add_shim(wrapper, replace_deps=True)

        return cache_decorator

    def args(self, *args: str, exclude: typing.Callable[..., bool] = None):

        def cache_decorator(f: FUNC_TYPE) -> FUNC_TYPE:
            idx_lookup = {arg: _index_of(arg, f) for arg in args}

            @functools.wraps(f)
            async def wrapper(*func_args, **func_kwargs):
                c, u = _pop(func_kwargs)
                if Cache._evicting or (exclude is not None and exclude(*func_args, **func_kwargs)):
                    return await f(*func_args, **func_kwargs)
                key = iter(func_kwargs[arg] if arg in func_kwargs else args[idx_lookup[arg]] for arg in args)
                return await self._get_from_cache(
                    c.redis,
                    f,
                    func_args,
                    func_kwargs,
                    self.store_prefix,
                    "args",
                    f.__name__,
                    *u.scopes,
                    *key
                )

            return _add_shim(wrapper, replace_deps=True)

        return cache_decorator

    def _evict(self, r: redis.Redis):
        Cache._evicted.add(self.name)
        set_key = f"{self.store_prefix}all".encode("ascii")
        keys = r.smembers(set_key)
        if keys is not None:
            for k in keys:
                r.delete(k)
        r.delete(set_key)

    def evict(self, f: FUNC_TYPE) -> FUNC_TYPE:

        @functools.wraps(f)
        async def wrapper(*func_args, **func_kwargs):
            Cache._evicting = True
            Cache._evicted.clear()
            try:
                c, u = _pop(func_kwargs)
                self._evict(c.redis)
                for cache in itertools.chain(self.evicts, Cache._always_evict):
                    if cache not in Cache._evicted:
                        Cache(cache)._evict(c.redis)
            finally:
                Cache._evicted.clear()
                Cache._evicting = False
            return await f(*func_args, **func_kwargs)

        return _add_shim(wrapper)

    async def operate(self, r: Request):
        """FastAPI
        """
        if Cache._evicting:
            yield None
        else:
            yield CacheOperator(self, r.state.cache)

    def use(self, f: FUNC_TYPE) -> FUNC_TYPE:

        @functools.wraps(f)
        async def wrapper(*func_args, **func_kwargs):
            func_kwargs.pop(SHIM_KEY)
            return await f(*func_args, **func_kwargs)

        params = list()
        s = inspect.signature(f)
        for k, v in s.parameters.items():
            if v.default is Cache.Inject:
                v = v.replace(default=Depends(self.operate))
            params.append(v)

        wrapper.__signature__ = s.replace(parameters=params)

        return _add_shim(wrapper, replace_deps=True)


class CacheOperator:
    def __init__(self, p: 'Cache', r: redis.Redis):
        self.parent = p
        self.redis = r

    def set(
            self,
            *keys: typing.Any,
            data: typing.Union[str, bytes],
            prefix: typing.Literal["key", "args", "custom"] = "custom"
    ):
        key = f"{self.parent.store_prefix}{prefix}:".encode("ascii") + shash(keys)
        self.redis.set(key, data)
        self.redis.sadd(f"{self.parent.store_prefix}all".encode("ascii"), key)

    def get(
            self,
            *keys: typing.Any,
            prefix: typing.Literal["key", "args", "custom"] = "custom"
    ):
        key = f"{self.parent.store_prefix}{prefix}:".encode("ascii") + shash(keys)
        return self.redis.get(key)


Cache.Operator = CacheOperator
