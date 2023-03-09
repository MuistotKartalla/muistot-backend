import contextlib
from typing import Mapping, Any

from sqlalchemy import exc, text, Result
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncConnection

from .resultset import ResultSet
from ..config.config import Database


class DatabaseError(Exception):
    pass


class OperationalError(DatabaseError):
    pass


class IntegrityError(OperationalError):
    pass


class InterfaceError(DatabaseError):
    pass


class ConnectionWrapper:
    """Wraps connection operations to something a bit more concise
    """
    connection: AsyncConnection

    def __init__(self, connection: AsyncConnection):
        super(ConnectionWrapper, self).__init__()
        self.connection = connection

    @contextlib.asynccontextmanager
    async def _query(self, query: str, values: Mapping[str, Any]) -> Result:
        query = text(query)
        if values:
            result = await self.connection.execute(query, parameters=values)
        else:
            result = await self.connection.execute(query)
        yield result

    async def execute(self, query: str, values: Mapping[str, Any] = None):
        async with self._query(query, values):
            pass

    async def fetch_val(self, query: str, values: Mapping[str, Any] = None):
        async with self._query(query, values) as c:
            res = c.fetchone()
            return res[0] if res is not None else res

    async def fetch_one(self, query: str, values: Mapping[str, Any] = None):
        async with self._query(query, values) as c:
            res = c.mappings().fetchone()
            if res:
                return ResultSet(res.items())

    async def fetch_all(self, query: str, values: Mapping[str, Any] = None):
        async with self._query(query, values) as c:
            rs = c.mappings().fetchall()
            return [ResultSet(res.items()) for res in rs] if rs is not None else []

    async def iterate(self, query: str, values: Mapping[str, Any] = None):
        async with self._query(query, values) as c:
            rs = c.mappings()
            for res in rs:
                yield ResultSet(res.items())


class DatabaseProvider:
    """Abstracts database connectivity

    This class takes care of assigning database resources for incoming calls.
    Connections are taken from a common pool and are returned to it upon completion.
    The order of the connections is not enforced after creation, so they will be unordered after a while.
    The initial allocation aims to provide a fair starting point for the connections so that no single thread
    gets overloaded with requests.
    """
    engine: AsyncEngine

    def __init__(self, config: Database):
        self.config = config

    def is_connected(self):
        return hasattr(self, "engine")

    async def connect(self):
        config = self.config
        self.engine = create_async_engine(
            f"{config.driver}://{config.user}:{config.password}@{config.host}:{config.port}/{config.database}",
            pool_pre_ping=True,
            pool_reset_on_return=True,
            pool_size=config.pool_size,
            pool_recycle=3600,
            pool_logging_name="Muistot Database Pool",
            pool_timeout=config.pool_timeout_seconds,
        )

    async def disconnect(self):
        await self.engine.dispose(close=True)
        del self.engine

    @contextlib.asynccontextmanager
    async def __call__(self):
        """Allocates a single connection
        """
        if not self.is_connected():
            raise OperationalError("Database not Running")
        try:
            async with self.engine.connect() as connection:
                async with connection.begin() as tsx:
                    yield ConnectionWrapper(connection)
                    if self.config.rollback:
                        await tsx.rollback()
                    else:
                        await tsx.commit()
        except exc.DBAPIError as e:
            if isinstance(e, exc.IntegrityError):
                raise IntegrityError() from e
            elif isinstance(e, exc.OperationalError):
                raise OperationalError() from e
            elif isinstance(e, exc.InterfaceError):
                raise InterfaceError() from e
            else:
                raise DatabaseError() from e
