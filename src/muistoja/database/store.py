from typing import Dict, Iterator

from .connection import DatabaseConnection
from ..config import Config
from ..logging import log


class DatabaseDependency:

    def __init__(self, name: str, database: DatabaseConnection):
        self.database = database
        self.name = name

    async def __call__(self):
        c = self.database
        if not c.connected:
            if not c.connected:
                try:
                    await c.connect()
                except c.OperationalError as e:
                    log.error(f"Failed to connect database: {self.name}", exc_info=e)
                    raise e
        async with c.begin() as db:
            yield db


class _Databases:
    _data: Dict[str, DatabaseDependency]
    default: DatabaseDependency

    def __init__(self):
        self._data = dict()
        for k, v in Config.db.items():
            db = DatabaseConnection(v)
            self._data[k] = DatabaseDependency(k, db)

    def __getattr__(self, item) -> DatabaseDependency:
        return self._data[item]

    def __iter__(self) -> Iterator[DatabaseDependency]:
        return self._data.values().__iter__()


Databases = _Databases()


async def connect():
    """Try to connect to all declared connections
    """
    for dbd in Databases:
        db = dbd.database
        try:
            await db.connect()
        except db.OperationalError as e:
            log.warning(f"Failed to connect to database: {dbd.name}", exc_info=e)


async def disconnect():
    """Disconnect all opened connections
    """
    for dbd in Databases:
        db = dbd.database
        try:
            await db.disconnect()
        except db.OperationalError as e:
            log.warning(f"Failed to disconnect from database: {dbd.name}", exc_info=e)
