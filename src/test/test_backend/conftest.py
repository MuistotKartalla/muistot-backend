import pytest
from muistoja.database import Databases


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def db_instance(anyio_backend):
    inst = Databases.default.database
    while True:
        try:
            await inst.connect()
            break
        except inst.OperationalError:
            pass
    try:
        yield inst
    finally:
        await inst.disconnect()
        del inst


@pytest.fixture(scope="function")
async def db(db_instance, anyio_backend):
    async with db_instance.begin() as c:
        await c.execute('ROLLBACK')
        await c.execute('SET autocommit = 1')
        yield c


@pytest.fixture(scope="function")
async def rollback(db, anyio_backend):
    await db.execute('COMMIT')
    await db.execute('SET autocommit = 0')
    await db.execute('BEGIN')
    yield db
    await db.execute('ROLLBACK')
