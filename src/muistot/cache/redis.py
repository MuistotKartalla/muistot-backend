import typing

import redis
from fastapi import FastAPI


class FastStorage:
    redis: typing.Optional[redis.Redis]

    def __init__(self, url: str):
        self.url = url
        self.redis = None

    def connect(self):
        if self.redis is None:
            self.redis = redis.from_url(self.url)

    def disconnect(self):
        if self.redis is not None:
            i = self.redis
            self.redis = None
            i.close()

    def set(self, key: str, value: str, /, prefix: str = "custom:", ttl: int = None):
        self.redis.set(f"{prefix}{key}", value, ex=ttl)

    def get(self, key: str, /, prefix: str = "custom:") -> typing.Optional[typing.Union[str, bytes]]:
        return self.redis.get(f"{prefix}{key}")

    def delete(self, key: str, /, prefix: str = "custom:"):
        return self.redis.delete(f"{prefix}{key}")

    def exists(self, *keys: str, prefix: str = "custom:") -> bool:
        return bool(self.redis.exists(*iter(f"{prefix}{key}" for key in keys)))


def register_redis_cache(app: FastAPI):
    from ..config import Config
    instance = FastStorage(Config.cache.redis_url)
    app.state.FastStorage = instance

    @app.middleware("http")
    async def add_cache(r, call_next):
        r.state.cache = instance
        instance.connect()
        return await call_next(r)

    @app.on_event("startup")
    async def close_cache():
        instance.connect()

    @app.on_event("shutdown")
    async def close_cache():
        instance.disconnect()


class EmptyCache(FastStorage):

    def __init__(self):
        super(EmptyCache, self).__init__("")

    def __getattr__(self, *_, **__):
        return lambda *_, **__: None
