import pytest
from muistot.config import Config
from muistot.database.store import _Databases, DatabaseDependency


def test_databases():
    d = _Databases()
    for k in Config.database.keys():
        assert isinstance(getattr(d, k), DatabaseDependency)
    for db in d:
        assert isinstance(db, DatabaseDependency)


def test_dependency():
    import asyncio
    import contextlib

    class Mock:

        connect_called = False
        beginned = False
        is_connected = False

        async def connect(self):
            Mock.connect_called = True

        @contextlib.asynccontextmanager
        async def __call__(self):
            Mock.beginned = True
            yield

    dp = DatabaseDependency('test-name', Mock())
    assert hasattr(dp.__call__(), '__anext__')  # FastAPI will wrap this
    assert dp.name == 'test-name'

    async def run():
        async with contextlib.asynccontextmanager(dp.__call__)():
            pass

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(run())
    finally:
        loop.close()

    assert Mock.connect_called
    assert Mock.beginned


def test_dependency_fail_to_connect():
    import asyncio
    import contextlib

    class Mock:

        OperationalError = RuntimeError
        is_connected = False

        async def connect(self):
            raise RuntimeError()

    dp = DatabaseDependency('test-name', Mock())

    async def run():
        async with contextlib.asynccontextmanager(dp.__call__)():
            pass

    with pytest.raises(RuntimeError):
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(run())
        finally:
            loop.close()
