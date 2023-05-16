from hashlib import sha1

from fastapi import HTTPException, status, Request
from redis import Redis


def ratelimit_via_redis_host_and_key(r: Request, prefix: str, key: str, ttl_seconds: int):
    cache: Redis = r.state.redis
    host_key = f"email-login:{prefix}:{sha1(r.client.host.encode()).hexdigest()}"
    key_key = f"email-login:{prefix}:{sha1(key.encode()).hexdigest()}"
    if cache.exists(key_key, host_key):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
    else:
        cache.set(key_key, "", ex=ttl_seconds)
        cache.set(host_key, "", ex=ttl_seconds)
