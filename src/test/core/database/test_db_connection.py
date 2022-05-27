import pytest
from muistot.database.connection import DatabaseConnection, Database, ConnectionMaster, ConnectionExecutor
from muistot.database.connection import allocate_fair, named_to_pyformat


@pytest.fixture
def cfg():
    from muistot.config import Config
    from muistot.config.config import Database
    db = Database(**Config.database["default"].dict())
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
    assert not c.is_connected
    c._connected = True
    assert c.is_connected


@pytest.mark.anyio
async def test_connection_bad_host_config(cfg):
    c = DatabaseConnection(cfg)
    with pytest.raises(DatabaseConnection.OperationalError):
        await c.connect()


@pytest.mark.anyio
async def test_connection_double_init_no_raise(cfg):
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
        async with c():
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
        async with c():
            pass


@pytest.mark.anyio
async def test_begin_commit(cfg):
    calls = {"begin", "commit", "ping"}

    class Connection:

        async def begin(self):
            calls.remove("begin")

        async def commit(self):
            calls.remove("commit")

        async def ping(self):
            calls.remove("ping")

    c = DatabaseConnection(cfg)
    c._connected = True
    c._connections.append(Connection())
    async with c() as cc:
        assert isinstance(cc, Connection)

    assert len(calls) == 0
    assert len(c._connections) == 1  # returned


@pytest.mark.anyio
async def test_begin_rollback(cfg):
    calls = {"begin", "rollback", "ping"}

    class Connection:

        async def begin(self):
            calls.remove("begin")

        async def rollback(self):
            calls.remove("rollback")

        async def ping(self):
            calls.remove("ping")

    c = DatabaseConnection(cfg)
    c._connected = True
    c._connections.append(Connection())

    with pytest.raises(RuntimeError):
        async with c() as cc:
            assert isinstance(cc, Connection)
            raise RuntimeError()

    assert len(calls) == 0
    assert len(c._connections) == 1  # returned


@pytest.mark.anyio
async def test_connection_yielding(cfg):
    class Connection:

        async def begin(self):
            pass

        async def commit(self):
            pass

        async def ping(self):
            pass

    c = DatabaseConnection(cfg)
    c._connected = True
    c._connections.append(Connection())

    async with c() as cc:  # Should be a contextmanager
        assert isinstance(cc, Connection)


@pytest.mark.anyio
async def test_connection_iterate_handles_none(cfg):
    async def nothing(*_, **__):
        return None

    class Executor:

        @staticmethod
        def submit(*_, **__):
            from concurrent.futures import Future
            f = Future()
            f.set_result(None)
            return f

    conn = ConnectionExecutor(None, Executor)
    conn._fetch_all = nothing

    data = [o async for o in conn.iterate("")]
    assert len(data) == 0
