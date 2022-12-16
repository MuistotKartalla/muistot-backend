from fastapi import HTTPException, status, Request


def ratelimit_via_redis_host_and_key(r: Request, key: str):
    cache = r.state.cache
    if cache.exists(key, r.client.host, prefix="email-login:"):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
    else:
        cache.set(key, "", prefix="email-login:", ttl=20)
        cache.set(r.client.host, "", prefix="email-login:", ttl=20)
