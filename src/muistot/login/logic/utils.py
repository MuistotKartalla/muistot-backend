from hashlib import sha1

from fastapi import HTTPException, status
from redis import Redis


def ratelimit(redis: Redis, prefix: str, *keys: str, ttl_seconds: int):
    keys = [f"email-login:{prefix}:{sha1(key.encode()).hexdigest()}" for key in keys]
    if redis.exists(*keys):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
    else:
        for key in keys:
            redis.set(key, "", ex=ttl_seconds)
