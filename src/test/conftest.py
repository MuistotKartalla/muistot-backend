import databases
import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
async def db():
    db_instance = databases.Database("mysql://root:test@localhost:5601/muistot", force_rollback=False)
    await db_instance.connect()
    try:
        yield db_instance
    finally:
        await db_instance.disconnect()


@pytest.fixture
def client(db):
    old = main.Config.security.csrf.enabled
    main.Config.security.csrf.enabled = False
    with TestClient(main.app) as instance:
        yield instance
    main.Config.security.csrf.enabled = old
