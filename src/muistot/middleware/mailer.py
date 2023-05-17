from starlette.applications import ASGIApp
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from ..mailer import *


class MailerMiddleware(BaseHTTPMiddleware):
    DRIVERS = {
        impl.__name__: impl
        for impl in [
            ZonerMailer,
            ServerMailer,
            LogMailer,
        ]
    }

    @staticmethod
    def get(r: Request) -> Mailer:
        return r.state.mailer

    driver: str
    config: dict
    instance: Mailer

    def __init__(self, app: ASGIApp, driver: str, data: dict):
        super().__init__(app)
        self.driver = driver
        self.data = data
        self.instance = MailerMiddleware.DRIVERS[driver](**data)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.mailer = self.instance
        return await call_next(request)
