from logging import Logger
from time import time_ns

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class TimingMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp, logger: Logger) -> None:
        super(TimingMiddleware, self).__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time_ns()
        try:
            return await call_next(request)
        finally:
            self.logger.info(
                "%s request to %s took %.3f millis",
                request.method,
                request.url,
                (time_ns() - start) / 1E6,
            )
