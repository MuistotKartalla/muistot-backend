from types import SimpleNamespace
from typing import Dict

from starlette.applications import ASGIApp
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from ..config.models import Database as DatabaseConfig
from ..database import DatabaseProvider, Database


class DatabaseMiddleware(BaseHTTPMiddleware):
    instances: Dict[str, DatabaseProvider]

    @staticmethod
    def get(r: Request) -> Database:
        return r.state.databases

    @staticmethod
    async def default(r: Request) -> Database:
        async with r.state.databases.default() as database:
            yield database

    def __init__(self, app: ASGIApp, databases: Dict[str, DatabaseConfig]):
        super(DatabaseMiddleware, self).__init__(app)
        self.instances = {
            database: DatabaseProvider(config)
            for database, config in databases.items()
        }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.databases = SimpleNamespace(**self.instances)
        return await call_next(request)
