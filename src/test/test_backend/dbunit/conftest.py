import databases
import pytest
from muistoja.config import config_to_url
from pymysql.err import OperationalError


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def db(anyio_backend):
    from muistoja.config import Config
    db_instance = databases.Database(config_to_url(Config.db["default"]))
    while True:
        try:
            await db_instance.connect()
            break
        except OperationalError:
            pass
    try:
        yield db_instance
    finally:
        await db_instance.disconnect()
