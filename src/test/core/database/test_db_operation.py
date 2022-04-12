import pytest
from muistot.config import Config
from muistot.database.connection import DatabaseConnection


@pytest.fixture(scope="function")
async def db_instance(anyio_backend):
    inst = DatabaseConnection(Config.database["default"])
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


@pytest.mark.anyio
async def test_connection_reconnect(db_instance):
    next_db = db_instance._connections[0]
    old_sock = next_db.connection._sock
    old_sock.close()
    next_db.connection._sock = None
    # Next Connection
    async with db_instance() as db:
        assert db is next_db
        assert await db.fetch_val("SELECT 1")
    assert await next_db.fetch_val("SELECT 1")


@pytest.mark.anyio
async def test_connection_intermittent_failure(db_instance):
    from pymysql.err import InterfaceError
    # Next Connection
    with pytest.raises(InterfaceError) as e:
        async with db_instance() as db:
            assert await db.fetch_val("SELECT 1")
            old_sock = db.connection._sock
            old_sock.close()
            db.connection._sock = None

    # Commit and Rollback both should throw
    assert isinstance(e.value, InterfaceError)
    assert isinstance(e.value.__cause__, InterfaceError)
