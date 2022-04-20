import contextlib
import functools
import hashlib
import inspect
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


class DelayMarker:
    """
    This is used to delay database dependency gets to not run out of connections
    """
    actual_dependency: DatabaseDependency


STORAGE = "entity-cache:{}:"
SHIM_KEY = "__cache_shim__"
TTL = Config.cache.cache_ttl

FUNC_TYPE = typing.Callable[..., typing.Awaitable[BaseModel]]


def get_database_delayed(actual_dependency):
    marker = DelayMarker()
    marker.actual_dependency = contextlib.asynccontextmanager(actual_dependency)

    async def database_depends_delay_shim():
        return marker

    return database_depends_delay_shim


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
                v = v.replace(default=Depends(get_database_delayed(v.default.dependency), use_cache=False))
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
    evicting = False
    evicted = set()

    def __init__(self, prefix: str, *, evicts: typing.Set[str] = None):
        self.name = prefix
        self.store_prefix = STORAGE.format(prefix)
        self.evicts = list(evicts) if evicts is not None else list()
        # Locking
        self.lock = threading.Lock()

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
                    """
                    Replaces any Delayed dependencies and calls the actual endpoint function
                    
                    This allows leaving the actual database resolution to the last possible moment
                    to avoid consuming connections for calls that do not need them.
                    
                    This will increase the amount of concurrent connections the high load endpoints
                    can take without running out of connections.
                    
                    This doesn't however prevent the program from running out of connections if there
                    are many calls made to endpoints without caching support.
                    """
                    async with contextlib.AsyncExitStack() as stack:
                        new_kwargs = dict()
                        for k, v in kwargs.items():
                            if type(v) != DelayMarker:
                                new_kwargs[k] = v
                            else:
                                new_kwargs[k] = await stack.enter_async_context(v.actual_dependency())
                        response_entity: BaseModel = await f(*args, **new_kwargs)
                        r.sadd(f"{prefix}all".encode("ascii"), key)
                        r.set(key, response_entity.json(), ex=TTL)
                        return response_entity
        return Response(status_code=200, content=data, media_type=JSONResponse.media_type)

    def key(self, key: str):

        def cache_decorator(f: FUNC_TYPE) -> FUNC_TYPE:
            @functools.wraps(f)
            async def wrapper(*args, **kwargs):
                c, u = _pop(kwargs)
                if Cache.evicting:
                    return await f(*args, **kwargs)
                return await self._get_from_cache(
                    c.redis,
                    f,
                    args,
                    kwargs,
                    self.store_prefix,
                    "key",
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
                if Cache.evicting or (exclude is not None and exclude(*func_args, **func_kwargs)):
                    return await f(*func_args, **func_kwargs)
                key = iter(func_kwargs[arg] if arg in func_kwargs else args[idx_lookup[arg]] for arg in args)
                return await self._get_from_cache(
                    c.redis,
                    f,
                    func_args,
                    func_kwargs,
                    self.store_prefix,
                    "args",
                    *u.scopes,
                    *key
                )

            return _add_shim(wrapper, replace_deps=True)

        return cache_decorator

    def _evict(self, r: redis.Redis):
        Cache.evicted.add(self.name)
        set_key = f"{self.store_prefix}all".encode("ascii")
        keys = r.smembers(set_key)
        if keys is not None:
            for k in keys:
                r.delete(k)
        r.delete(set_key)

    def evict(self, f: FUNC_TYPE) -> FUNC_TYPE:

        @functools.wraps(f)
        async def wrapper(*func_args, **func_kwargs):
            Cache.evicting = True
            Cache.evicted.clear()
            try:
                c, u = _pop(func_kwargs)
                self._evict(c.redis)
                for cache in self.evicts:
                    if cache not in Cache.evicted:
                        Cache(cache)._evict(c.redis)
            finally:
                Cache.evicted.clear()
                Cache.evicting = False
            return await f(*func_args, **func_kwargs)

        return _add_shim(wrapper)
