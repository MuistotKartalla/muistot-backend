from .decorator import Cache
from .redis import register_redis_cache, FastStorage

__all__ = [
    "register_redis_cache",
    "FastStorage",
    "Cache",
]
