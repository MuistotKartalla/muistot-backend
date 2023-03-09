from typing import Dict, Iterator

from .connection import DatabaseProvider
from ..config import Config
from ..logging import log


def create_connection(database):
    return DatabaseProvider(database)


class DatabaseDependency:

    def __init__(self, name: str, database_instance):
        self.database = database_instance
        self.name = name

    async def __call__(self):
        c = self.database
        if not c.is_connected:
            try:
                await c.connect()
            except c.OperationalError as e:
                log.error(f"Failed to connect database: {self.name}", exc_info=e)
                raise e
        async with c() as db:
            yield db


class _Databases:
    _data: Dict[str, DatabaseDependency]
    default: DatabaseDependency

    def __init__(self):
        self._data = dict()
        for k, v in Config.database.items():
            self._data[k] = DatabaseDependency(k, create_connection(v))

    def __getattr__(self, item) -> DatabaseDependency:
        return self._data[item]

    def __iter__(self) -> Iterator[DatabaseDependency]:
        return self._data.values().__iter__()


Databases = _Databases()


def register_databases(app):
    app.state.Databases = Databases

    @app.on_event("startup")
    async def connect():
        """Try to connect to all declared connections
        """
        for dbd in app.state.Databases:
            db = dbd.database
            try:
                await db.connect()
            except db.OperationalError as e:
                log.warning(f"Failed to connect to database: {dbd.name}", exc_info=e)

    @app.on_event("shutdown")
    async def disconnect():
        """Disconnect all opened connections
        """
        for dbd in app.state.Databases:
            db = dbd.database
            try:
                await db.disconnect()
            except db.OperationalError as e:
                log.warning(f"Failed to disconnect from database: {dbd.name}", exc_info=e)
