import pytest
from muistot.database import DatabaseProvider, DatabaseError, InterfaceError, IntegrityError, OperationalError
from sqlalchemy import exc


class MockThrowerEngine:

    def __init__(self, exception):
        self.exception = exception

    def connect(self):
        raise self.exception


@pytest.mark.parametrize('raised,expected', [
    (exc.OperationalError(None, None, None), OperationalError),
    (exc.IntegrityError(None, None, None), IntegrityError),
    (exc.InterfaceError(None, None, None), InterfaceError),
    (exc.DatabaseError(None, None, None), DatabaseError),
])
@pytest.mark.anyio
async def test_raising(raised, expected):
    d = DatabaseProvider(None)
    d.engine = MockThrowerEngine(raised)

    with pytest.raises(expected):
        async with d():
            pass


@pytest.mark.parametrize('rb', [
    True,
    False,
])
@pytest.mark.anyio
async def test_rollback_works(rb):
    called = set()

    class MockConfig:
        rollback: bool = rb

    class MockEngine:

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return self

        def connect(self):
            return self

        def begin(self):
            return self

        async def rollback(self):
            called.add('rollback')

        async def commit(self):
            called.add('commit')

    d = DatabaseProvider(MockConfig())
    d.engine = MockEngine()

    async with d():
        pass

    assert called == {'rollback' if rb else 'commit'}, 'Failed to call correct method'
