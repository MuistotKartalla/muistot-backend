import redis
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RedisMiddleware(BaseHTTPMiddleware):

    def __init__(self, app, url: str):
        super(RedisMiddleware, self).__init__(app)
        self.url = url
        self.redis = redis.from_url(url)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.redis = self.redis
        return await call_next(request)
