import pytest

from muistot.backend.services.me import *
from muistot.database import IntegrityError


class MockManager:

    def __getattr__(self, item):
        return lambda *_, **__: None


@pytest.mark.anyio
async def test_exists_null_guard():
    assert await check_username_not_exists(None, None) is None


@pytest.mark.anyio
async def test_exists_raise():
    class MockDB:

        async def fetch_val(self, *_, **__):
            return True

    with pytest.raises(HTTPException) as e:
        await check_username_not_exists(MockDB(), "")

    assert e.value.status_code == 409


@pytest.mark.anyio
async def test_email_conflict():
    class MockDB:
        IntegrityError = RuntimeError

        async def fetch_one(self, *_, **__):
            return [True, False]

    with pytest.raises(HTTPException) as e:
        await change_email(MockDB(), "", "", None)

    assert e.value.status_code == status.HTTP_409_CONFLICT


@pytest.mark.anyio
async def test_change_email_handles_integrity_error():
    class MockDB:
        cnt = 0
        IntegrityError = RuntimeError

        async def fetch_one(self, *_, **__):
            MockDB.cnt += 1
            return [False, False]

        async def execute(self, *_, **__):
            MockDB.cnt += 1
            raise IntegrityError()

    with pytest.raises(HTTPException) as e:
        await change_email(MockDB(), "", "", MockManager())

    assert e.value.status_code == status.HTTP_409_CONFLICT
    assert MockDB.cnt == 2


@pytest.mark.anyio
async def test_change_username_handles_integrity_error():
    class MockDB:
        cnt = 0
        IntegrityError = RuntimeError

        async def fetch_val(self, *_, **__):
            MockDB.cnt += 1
            return False

        async def execute(self, *_, **__):
            MockDB.cnt += 1
            raise IntegrityError()

    with pytest.raises(HTTPException) as e:
        await change_username(MockDB(), "old", "new", MockManager())

    assert e.value.status_code == status.HTTP_409_CONFLICT
    assert MockDB.cnt == 2
