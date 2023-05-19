from typing import Callable

import pytest
from starlette.exceptions import HTTPException

from muistot.backend.repos.status import Status, MemoryStatus, SiteStatus, StatusProvider


class MockUser:
    def __init__(self, is_authenticated=False):
        self.is_authenticated = is_authenticated
        self.is_superuser = False
        self.identity = "test"


class MockDB:
    NULL: "MockDB"

    def __init__(self, **result):
        if "is_creator" not in result:
            result["is_creator"] = False
        if "is_admin" not in result:
            result["is_admin"] = False
        if "default_language" not in result:
            result["default_language"] = "fi"
        result["admin_posting"] = False
        result["auto_publish"] = False
        self.result = dict(**result)

    async def fetch_one(self, *_, **__):
        return self.result


MockDB.NULL = MockDB()
MockDB.NULL.result = None


def exists(base) -> Callable[[MockDB, MockUser], StatusProvider]:
    test_identifiers = {
        "comment": 1,
        "memory": 1,
        "site": "aaaa",
        "project": "aaaa",
    }

    class ExistTestHarness(base):
        identifiers = test_identifiers

        def __getattr__(self, item):
            return test_identifiers[item]

        def __init__(self, db, user):
            super().__init__()
            self.db = db
            self.user = user

    return ExistTestHarness


@pytest.mark.parametrize("cls", [
    MemoryStatus,
    SiteStatus,
])
@pytest.mark.anyio
async def test_none_result(cls):
    with pytest.raises(HTTPException) as e:
        await exists(cls)(MockDB.NULL, MockUser()).provide_status()
    assert "Project" in e.value.detail


@pytest.mark.parametrize("cls", [
    MemoryStatus,
])
@pytest.mark.anyio
async def test_site_not_found_result(cls):
    with pytest.raises(HTTPException) as e:
        await exists(cls)(MockDB(
            site_published=None,
        ), MockUser()).provide_status()
    assert "Site" in e.value.detail


@pytest.mark.parametrize("cls", [
    MemoryStatus,
    SiteStatus,
])
@pytest.mark.anyio
async def test_project_not_published_result(cls):
    with pytest.raises(HTTPException) as e:
        await exists(cls)(
            MockDB(
                site_published=True,
                memory_published=True,
                project_published=False,
            ), MockUser()).provide_status()
    assert "Project" in e.value.detail


@pytest.mark.parametrize("cls", [
    MemoryStatus,
])
@pytest.mark.anyio
async def test_site_not_published_result(cls):
    with pytest.raises(HTTPException) as e:
        await exists(cls)(MockDB(
            site_published=False,
            memory_published=True,
            project_published=True,
        ), MockUser()).provide_status()
    assert "Site" in e.value.detail


@pytest.mark.parametrize("cls,db", [
    (MemoryStatus, MockDB(
        is_creator=True,
        memory_published=False,
        site_published=True,
        project_published=True,
    )),
    (SiteStatus, MockDB(
        is_creator=True,
        site_published=False,
        project_published=True,
    )),
    (MemoryStatus, MockDB(
        is_creator=True,
        memory_published=False,
        site_published=False,
        project_published=False,
        is_admin=True,
    )),
    (SiteStatus, MockDB(
        is_creator=True,
        site_published=False,
        project_published=False,
        is_admin=True,
    )),
])
@pytest.mark.anyio
async def test_status_for_unpublished(cls, db):
    s = await exists(cls)(db, MockUser(is_authenticated=True)).provide_status()
    assert Status.OWN in s
