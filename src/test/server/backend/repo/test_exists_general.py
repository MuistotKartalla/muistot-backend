import pytest
from fastapi import HTTPException
from muistot.backend.repos.exists.memory import MemoryExists
from muistot.backend.repos.exists.site import SiteExists


def exists(base):
    class ProxyExists(base):
        comment = 1
        memory = 1
        site = "aaaa"
        project = "aaaa"

    return ProxyExists


class MockUser:
    def __init__(self, is_authenticated=False):
        self.is_authenticated = is_authenticated
        self.identity = "test"


class MockDB:
    NULL: 'MockDB'

    def __init__(self, **result):
        if "is_creator" not in result:
            result["is_creator"] = False
        if "is_admin" not in result:
            result["is_admin"] = False
        if "comment_published" not in result:
            result["comment_published"] = False
        if "default_language" not in result:
            result["default_language"] = "fi"
        result["admin_posting"] = False
        result["auto_publish"] = False
        self.result = dict(**result)

    async def fetch_one(self, *_, **__):
        return self.result


_n = MockDB()
_n.result = None
MockDB.NULL = _n


@pytest.mark.parametrize("cls", [
    MemoryExists,
    SiteExists,
])
@pytest.mark.anyio
async def test_none_result(cls):
    with pytest.raises(HTTPException) as e:
        await exists(cls)(MockDB.NULL, MockUser()).exists()
    assert "Project" in e.value.detail


@pytest.mark.parametrize("cls", [
    MemoryExists,
])
@pytest.mark.anyio
async def test_site_not_found_result(cls):
    with pytest.raises(HTTPException) as e:
        await exists(cls)(MockDB(
            site_published=None,
        ), MockUser()).exists()
    assert "Site" in e.value.detail


@pytest.mark.parametrize("cls", [
    MemoryExists,
    SiteExists,
])
@pytest.mark.anyio
async def test_project_not_published_result(cls):
    with pytest.raises(HTTPException) as e:
        await exists(cls)(
            MockDB(
                site_published=True,
                memory_published=True,
                project_published=False,
            ), MockUser()).exists()
    assert "Project" in e.value.detail


@pytest.mark.parametrize("cls", [
    MemoryExists,
])
@pytest.mark.anyio
async def test_site_not_published_result(cls):
    with pytest.raises(HTTPException) as e:
        await exists(cls)(MockDB(
            site_published=False,
            memory_published=True,
            project_published=True,
        ), MockUser()).exists()
    assert "Site" in e.value.detail


@pytest.mark.parametrize("cls", [
    MemoryExists,
    SiteExists,
])
@pytest.mark.anyio
async def test_own_early_return(cls):
    s = await exists(cls)(MockDB(
        site_published=False,
        memory_published=False,
        project_published=False,
        is_creator=True,
        comment_published=False
    ), MockUser(is_authenticated=True)).exists()
    assert s.own
    assert not s.admin


@pytest.mark.parametrize("cls", [
    MemoryExists,
    SiteExists,
])
@pytest.mark.anyio
async def test_admin_early_return(cls):
    s = await exists(cls)(MockDB(
        site_published=False,
        memory_published=False,
        project_published=False,
        is_admin=True,
        comment_published=False
    ), MockUser(is_authenticated=True)).exists()
    assert not s.own
    assert s.admin
