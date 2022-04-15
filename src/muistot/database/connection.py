import asyncio as aio
import collections
import concurrent.futures
import contextlib
import functools
import re
from typing import Mapping, Collection, Iterable, Any, Deque

import pymysql

from .models import ResultSetCursor
from ..config.config import Database

_PATTERN = re.compile(r":(\w+)")
_REPLACE = r"%(\1)s"


@functools.lru_cache(maxsize=128)
def named_to_pyformat(query: str):
    """Converts from format preferred by Databases library

    For example:
    - SELECT 1 FROM users WHERE username = :user
    To:
    - SELECT 1 FROM users WHERE username = %(user)s

    This is for backwards compatibility.
    Keep in mind the REGEX is quite simple replacing EVERYTHING :xyz with %(xyz)s

    The function calls are cached (max. 128) so that this won't be a bottleneck.
    This does incur a warmup cost though on first invocation.
    """
    return _PATTERN.sub(_REPLACE, query)


def make_connection(config: Database):
    """Reasonable defaults for a connection

    Sets the cursor class to a custom one providing similar functionality to SQLAlchemy
    where the spread operators and spreading the result to multiple variables works as intended
    """
    c = pymysql.Connection(
        user=config.user,
        password=config.password,
        host=config.host,
        port=config.port,
        database=config.database,
        compress=False,
        charset="utf8mb4",
        cursorclass=ResultSetCursor,
        autocommit=False,
        defer_connect=True
    )
    return c


def allocate_fair(iterable):
    """Puts connection executor connections into consecutive order

    T2, T3, T4

    --> T2.1, T3.1, T4.1, T2.2, T3.2 ...

    This is completely fair allocation policy for the connections and does not care about their status
    """
    import itertools
    return itertools.chain(*zip(*iterable))


class ConnectionMaster:
    """Further abstracts ConnectionExecutor to allows many connections per thread

    One thread will be severely underutilized if only one connection is running on it.
    This class sets up many connection on one ThreadPoolExecutor, essentially making a
    single thread the owner of a bunch of threads.
    """

    def __init__(self, connections: Iterable[pymysql.Connection]):
        super(ConnectionMaster, self).__init__()
        self.worker = concurrent.futures.ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix=f'connection_worker'
        )
        self.workers = list(ConnectionExecutor(c, self.worker) for c in connections)

    def __iter__(self):
        return self.workers.__iter__()

    def __len__(self):
        return self.workers.__len__()

    def __del__(self):
        self.worker.shutdown(wait=False, cancel_futures=True)


class ConnectionExecutor:
    """PyMySQL is not thread safe so confining all operations to a single thread.

    Since everything is submitted to the Executor in order, the execution will happen in order
    in the same thread preventing deadlocks and threading issues, but will free up aio to do more
    processing in the meantime. This allows higher throughput especially if a query hangs or takes
    very long.
    """

    IntegrityError = pymysql.err.IntegrityError
    OperationalError = pymysql.err.OperationalError

    def __init__(self, connection: pymysql.Connection, executor: concurrent.futures.ThreadPoolExecutor):
        super(ConnectionExecutor, self).__init__()
        self.worker = executor
        self.connection = connection

    def submit(self, *args, **kwargs):
        return self.worker.submit(*args, **kwargs)

    @contextlib.contextmanager
    def _query(self, query, args) -> ResultSetCursor:
        args = None if args is None else dict(**args)
        c = self.connection.cursor()
        try:
            c.execute(named_to_pyformat(query), args)
            yield c
        finally:
            c.close()

    def _execute(self, query, args):
        with self._query(query, args):
            pass

    def _fetch_val(self, query, args):
        with self._query(query, args) as c:
            res = c.fetchone()
            # noinspection PyTypeChecker
            # ResultSet accepts ints
            return res[0] if res is not None else res

    def _fetch_one(self, query, args):
        with self._query(query, args) as c:
            return c.fetchone()

    def _fetch_all(self, query, args):
        with self._query(query, args) as c:
            res = c.fetchall()
            return list(res) if res is not None else list()

    async def execute(self, query: str, values: Mapping[str, Any] = None):
        await aio.get_running_loop().run_in_executor(self, self._execute, query, values)

    async def fetch_val(self, query: str, values: Mapping[str, Any] = None) -> Any:
        return await aio.get_running_loop().run_in_executor(self, self._fetch_val, query, values)

    async def fetch_one(self, query: str, values: Mapping[str, Any] = None) -> Mapping:
        return await aio.get_running_loop().run_in_executor(self, self._fetch_one, query, values)

    async def fetch_all(self, query: str, values: Mapping[str, Any] = None) -> Collection[Mapping]:
        return await aio.get_running_loop().run_in_executor(self, self._fetch_all, query, values)

    async def iterate(self, query: str, values: Mapping[str, Any] = None):
        data = await aio.get_running_loop().run_in_executor(self, self._fetch_all, query, values)
        if data is not None:
            for res in data:
                yield res

    async def rollback(self):
        await aio.get_running_loop().run_in_executor(self, self.connection.rollback)

    async def commit(self):
        await aio.get_running_loop().run_in_executor(self, self.connection.commit)

    async def begin(self):
        await aio.get_running_loop().run_in_executor(self, self.connection.begin)

    async def connect(self):
        await aio.get_running_loop().run_in_executor(self, self.connection.connect)

    async def close(self):
        await aio.get_running_loop().run_in_executor(self, self.connection.close)

    async def ping(self):
        await aio.get_running_loop().run_in_executor(self, self.connection.ping, True)


class DatabaseConnection:
    """Abstracts database connectivity

    This class takes care of assigning database resources for incoming calls.
    Connections are taken from a common pool and are returned to it upon completion.
    The order of the connections is not enforced after creation, so they will be unordered after a while.
    The initial allocation aims to provide a fair starting point for the connections so that no single thread
    gets overloaded with requests.
    """
    _connections: Deque[ConnectionExecutor]
    OperationalError = pymysql.err.OperationalError

    def __init__(self, config: Database):
        self.config = config
        self._masters = list()
        self._connections = collections.deque()
        self._connected = False

    def _wait_for_connection(self):
        import time
        start = time.time()
        while time.time() - start < self.config.max_wait:
            try:
                return self._connections.popleft()
            except IndexError:
                time.sleep(1E-10)
        raise DatabaseConnection.OperationalError()

    @property
    def is_connected(self):
        return self._connected

    async def connect(self):
        if self._connected:
            return
        self._masters.extend(
            ConnectionMaster(make_connection(self.config) for _ in range(0, self.config.cpw))
            for _ in range(0, self.config.workers)
        )
        self._connections.extend(allocate_fair(self._masters))
        try:
            for c in self._connections:
                await c.connect()
        except BaseException as e:
            await self.disconnect()
            raise e
        self._connected = True

    async def disconnect(self):
        for c in self._connections:
            await c.close()
        self._connections.clear()
        del self._masters
        self._masters = list()
        self._connected = False

    @contextlib.asynccontextmanager
    async def __call__(self):
        """Allocates a single connection
        """
        if not self._connected:
            raise DatabaseConnection.OperationalError('Database not Running')
        try:
            connection = self._connections.popleft()
        except IndexError:
            connection = self._wait_for_connection()
        try:
            await connection.ping()
            try:
                await connection.begin()
                yield connection
                await connection.commit()
            except BaseException as e:
                try:
                    await connection.rollback()
                except BaseException as ex:
                    raise ex from e
                raise e
        finally:
            self._connections.append(connection)


Database = ConnectionExecutor
