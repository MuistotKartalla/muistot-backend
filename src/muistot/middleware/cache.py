import re
from hashlib import sha1

from redis import Redis
from starlette.applications import ASGIApp
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse, iterate_in_threadpool


class UnauthenticatedCacheMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp, url: str, ttl: int = 300):
        super(UnauthenticatedCacheMiddleware, self).__init__(app)
        self.url = url
        self.redis = Redis.from_url(url)
        self.ttl = ttl
        self.config = {
            "projects": {
                "path": re.compile("^/projects$"),
                "evict": [
                    "projects",
                ]
            },
            "project": {
                "path": re.compile("^/projects/([^/]+)$"),
                "evict": [
                    "projects",
                    "project",
                ]
            },
            "sites": {
                "path": re.compile("^/projects/([^/]+)/sites$"),
                "evict": [
                    "projects",
                    "project",
                    "sites",
                ]
            },
            "site": {
                "path": re.compile("^/projects/([^/]+)/sites/([^/]+)$"),
                "evict": [
                    "projects",
                    "project",
                    "sites",
                    "site",
                ]
            },
            "memories": {
                "path": re.compile("^/projects/([^/]+)/sites/([^/]+)/memories$"),
                "evict": [
                    "projects",
                    "project",
                    "sites",
                    "site",
                    "memories",
                ]
            },
            "memory": {
                "path": re.compile("^/projects/([^/]+)/sites/([^/]+)/memories/([^/]+)$"),
                "evict": [
                    "projects",
                    "project",
                    "sites",
                    "site",
                    "memories",
                    "memory",
                ]
            },
            "publish": {
                "path": re.compile("publish(?:\?.*?)?$"),
                "evict": [
                    "projects",
                    "project",
                    "sites",
                    "site",
                    "memories",
                    "memory",
                ]
            },
        }

    def __del__(self):
        self.redis.close()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Checks if request is eligible for caching

        This implementation only caches GETs and purges on other methods if they succeed.
        """
        request.state.cache = self.redis
        method = request.method.upper()
        if not request.user.is_authenticated and method in {"GET", "POST", "PATCH", "PUT", "DELETE"}:
            for cache_id, cache_config in self.config.items():
                cache_match = cache_config["path"].fullmatch(request.url.path)
                if cache_match is not None:
                    key = ":".join((
                        'cache',
                        cache_id,
                        *(sha1(part.encode()).hexdigest() for part in cache_match.groups()),
                    ))
                    if method == "GET":
                        cached = self.redis.get(key)
                        if not cached:
                            response = await call_next(request)
                            if 200 <= response.status_code < 300 and isinstance(response, StreamingResponse):
                                chunks = [chunk async for chunk in response.body_iterator]
                                body = b''.join(chunks)
                                response.body_iterator = iterate_in_threadpool(iter(chunks))
                                self.redis.set(key, body, ex=self.ttl)
                        else:
                            response = Response(
                                content=cached,
                                status_code=200,
                                headers={'Content-Type': 'application/json'}
                            )
                        return response
                    else:
                        response = await call_next(request)
                        if 200 <= response.status_code < 300:
                            self.redis.flushdb(asynchronous=True)
                        return response
        return await call_next(request)
