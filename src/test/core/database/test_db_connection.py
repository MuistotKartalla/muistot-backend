import pytest
from muistot.database.connection import DatabaseConnection, Database, ConnectionMaster, ConnectionExecutor
from muistot.database.connection import allocate_fair, named_to_pyformat


@pytest.fixture
def cfg():
    from muistot.config import Config
    from muistot.config.config import Database
    db = Database(**Config.db["default"].dict())
    db.host = 'localhost'
    db.port = 8080
    db.max_wait = 1
    yield db


@pytest.mark.parametrize("query, expected", [
    ("SELECT :a", "SELECT %(a)s"),
    ("SELECT a = :name FROM abc WHERE abc.name = :cde", "SELECT a = %(name)s FROM abc WHERE abc.name = %(cde)s")
])
def test_change_parameters(query, expected):
    assert named_to_pyformat(query) == expected


def test_allocation():
    a = [1, 2, 3]
    b = ["a", "b", "c"]
    assert list(allocate_fair((a, b))) == [1, "a", 2, "b", 3, "c"]


def test_import():
    assert Database is ConnectionExecutor


def test_master_iter():
    m = ConnectionMaster(list())
    m.workers = [1, 2, 3]
    assert list(m) == [1, 2, 3]


def test_master_delete():
    m = ConnectionMaster(list())
    w = m.worker
    del m
    with pytest.raises(RuntimeError):
        w.submit(None)


def test_connection_status():
    c = DatabaseConnection(None)
    assert not c.connected
    c._connected = True
    assert c.connected


@pytest.mark.anyio
async def test_connection_bad_host_config(cfg):
    c = DatabaseConnection(cfg)
    with pytest.raises(DatabaseConnection.OperationalError):
        await c.connect()


@pytest.mark.anyio
async def test_connection_no_double_init(cfg):
    c = DatabaseConnection(cfg)
    c._connected = True
    assert await c.connect() is None


@pytest.mark.anyio
async def test_connection_waiter_throws(cfg):
    c = DatabaseConnection(cfg)
    with pytest.raises(DatabaseConnection.OperationalError):
        c._wait_for_connection()


@pytest.mark.anyio
async def test_no_begin_if_not_started(cfg):
    c = DatabaseConnection(cfg)
    with pytest.raises(DatabaseConnection.OperationalError):
        async with c.begin():
            pass


@pytest.mark.anyio
async def test_begin_waiter(cfg):
    waited = [False]

    def wc():
        waited[0] = True
        raise RuntimeError()

    c = DatabaseConnection(cfg)
    c._connected = True
    c._wait_for_connection = wc

    with pytest.raises(RuntimeError):
        async with c.begin():
            pass


@pytest.mark.anyio
async def test_begin_commit(cfg):
    calls = {"begin", "commit"}

    class Connection:

        async def begin(self):
            calls.remove("begin")

        async def commit(self):
            calls.remove("commit")

    c = DatabaseConnection(cfg)
    c._connected = True
    c._connections.append(Connection())
    async with c.begin() as cc:
        assert isinstance(cc, Connection)

    assert len(calls) == 0
    assert len(c._connections) == 1  # returned


@pytest.mark.anyio
async def test_begin_rollback(cfg):
    calls = {"begin", "rollback"}

    class Connection:

        async def begin(self):
            calls.remove("begin")

        async def rollback(self):
            calls.remove("rollback")

    c = DatabaseConnection(cfg)
    c._connected = True
    c._connections.append(Connection())

    with pytest.raises(RuntimeError):
        async with c.begin() as cc:
            assert isinstance(cc, Connection)
            raise RuntimeError()

    assert len(calls) == 0
    assert len(c._connections) == 1  # returned


@pytest.mark.anyio
async def test_fastapi_compatibility_yielding(cfg):
    class Connection:

        async def begin(self):
            pass

        async def commit(self):
            pass

    c = DatabaseConnection(cfg)
    c._connected = True
    c._connections.append(Connection())

    async for cc in c():  # FastAPI wants plain generators
        assert isinstance(cc, Connection)
