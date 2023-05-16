from asyncio import sleep

import pytest
import redis

from muistot.config import Config
from muistot.database import Database, DatabaseProvider, OperationalError


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def db_instance(anyio_backend) -> DatabaseProvider:
    inst = DatabaseProvider(Config.database["default"])
    i = 10
    while True:
        try:
            async with inst():
                break
        except OperationalError:
            """Database not ready
            """
            i -= 1
            if i <= 0:
                pytest.fail("Database not available")
            await sleep(1)
    try:
        yield inst
    finally:
        del inst


@pytest.fixture(scope="function")
async def db(db_instance) -> Database:
    async with db_instance() as c:
        await c.execute('ROLLBACK')
        await c.execute('SET autocommit = 1')
        yield c
        # Return to right state
        await c.execute('SET autocommit = 0')


@pytest.fixture(scope="session")
def cache_redis():
    yield redis.from_url(Config.cache.redis_url)


@pytest.fixture(scope="session")
def session_redis():
    yield redis.from_url(Config.sessions.redis_url)
