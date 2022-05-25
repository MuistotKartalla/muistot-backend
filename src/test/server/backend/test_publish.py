import pytest
from fastapi import HTTPException
from muistot.backend.api.publish import check_exists, OrderBase


class MockRepo:

    def __init__(self, **values):
        self.data = dict(**values)

    async def fetch_one(self, *_, **__):
        return self.data


@pytest.mark.anyio
async def test_project_not_found():
    class Mock:
        async def fetch_one(self, *_, **__):
            return None

    with pytest.raises(HTTPException) as e:
        await check_exists(OrderBase(
            type="comment",
            identifier=1,
            parents={
                "project": "test",
                "site": "test",
                "memory": 1,
            }
        ), "test", Mock())
    assert "project" in e.value.detail


@pytest.mark.anyio
async def test_project_not_published_order():
    with pytest.raises(HTTPException) as e:
        await check_exists(OrderBase(
            type="project",
            identifier="aaaa",
        ), "test", MockRepo(project_not_published=True, admin=False), True)
    assert "project" in e.value.detail


@pytest.mark.anyio
async def test_project_not_published_parent():
    with pytest.raises(HTTPException) as e:
        await check_exists(OrderBase(
            type="site",
            identifier="aaaa",
            parents=dict(project="aaaa")
        ), "test", MockRepo(project_not_published=True, admin=False, sid=False), True)
    assert "project" in e.value.detail


@pytest.mark.anyio
async def test_site_not_found_order():
    with pytest.raises(HTTPException) as e:
        await check_exists(OrderBase(
            type="site",
            identifier="aaaa",
            parents=dict(
                project="aaaa",
            )
        ), "test", MockRepo(
            project_not_published=False,
            pid=False,
            sid=True,
            admin=False
        ), True)
    assert "site" in e.value.detail


@pytest.mark.anyio
async def test_site_not_published_order():
    with pytest.raises(HTTPException) as e:
        await check_exists(OrderBase(
            type="site",
            identifier="aaaa",
            parents=dict(
                project="aaaa",
            )
        ), "test", MockRepo(
            project_not_published=False,
            pid=False,
            site_not_published=True,
            sid=False,
            mid=False,
            admin=False
        ), True)
    assert "site" in e.value.detail


@pytest.mark.anyio
async def test_site_not_found_parent():
    with pytest.raises(HTTPException) as e:
        await check_exists(OrderBase(
            type="memory",
            identifier=1,
            parents=dict(
                project="aaaa",
                site="aaaa",
            )
        ), "test", MockRepo(
            project_not_published=False,
            pid=False,
            sid=True,
            mid=False,
            admin=False
        ), True)
    assert "site" in e.value.detail


@pytest.mark.anyio
async def test_site_not_published_parent():
    with pytest.raises(HTTPException) as e:
        await check_exists(OrderBase(
            type="memory",
            identifier=1,
            parents=dict(
                project="aaaa",
                site="aaaa",
            )
        ), "test", MockRepo(
            project_not_published=False,
            pid=False,
            site_not_published=True,
            sid=False,
            mid=False,
            admin=False
        ), True)
    assert "site" in e.value.detail


@pytest.mark.anyio
async def test_memory_not_found_order():
    with pytest.raises(HTTPException) as e:
        await check_exists(OrderBase(
            type="memory",
            identifier=1,
            parents=dict(
                project="aaaa",
                site="aaaa",
            )
        ), "test", MockRepo(
            project_not_published=False,
            pid=False,
            site_not_published=False,
            sid=False,
            mid=True,
            admin=False
        ), True)
    assert "memory" in e.value.detail


@pytest.mark.anyio
async def test_memory_not_published_order():
    with pytest.raises(HTTPException) as e:
        await check_exists(OrderBase(
            type="memory",
            identifier=1,
            parents=dict(
                project="aaaa",
                site="aaaa",
            )
        ), "test", MockRepo(
            project_not_published=False,
            pid=False,
            site_not_published=False,
            sid=False,
            memory_not_published=True,
            mid=False,
            admin=False
        ), True)
    assert "memory" in e.value.detail


@pytest.mark.anyio
async def test_memory_not_found_parent():
    with pytest.raises(HTTPException) as e:
        await check_exists(OrderBase(
            type="comment",
            identifier=1,
            parents=dict(
                project="aaaa",
                site="aaaa",
                memory=1
            )
        ), "test", MockRepo(
            project_not_published=False,
            pid=False,
            site_not_published=False,
            sid=False,
            mid=True,
            admin=False
        ), True)
    assert "memory" in e.value.detail


@pytest.mark.anyio
async def test_memory_not_published_parent():
    with pytest.raises(HTTPException) as e:
        await check_exists(OrderBase(
            type="comment",
            identifier=1,
            parents=dict(
                project="aaaa",
                site="aaaa",
                memory=1
            )
        ), "test", MockRepo(
            project_not_published=False,
            pid=False,
            site_not_published=False,
            sid=False,
            memory_not_published=True,
            mid=False,
            cid=False,
            admin=False
        ), True)
    assert "memory" in e.value.detail


@pytest.mark.anyio
async def test_comment_not_found_order():
    with pytest.raises(HTTPException) as e:
        await check_exists(OrderBase(
            type="comment",
            identifier=1,
            parents=dict(
                project="aaaa",
                site="aaaa",
                memory=1
            )
        ), "test", MockRepo(
            project_not_published=False,
            pid=False,
            site_not_published=False,
            sid=False,
            memory_not_published=False,
            mid=False,
            cid=True,
            admin=False
        ), True)
    assert "comment" in e.value.detail


@pytest.mark.anyio
async def test_comment_not_published_order():
    with pytest.raises(HTTPException) as e:
        await check_exists(OrderBase(
            type="comment",
            identifier=1,
            parents=dict(
                project="aaaa",
                site="aaaa",
                memory=1
            )
        ), "test", MockRepo(
            project_not_published=False,
            pid=False,
            site_not_published=False,
            sid=False,
            memory_not_published=False,
            mid=False,
            comment_not_published=True,
            cid=False,
            admin=False
        ), True)
    assert "comment" in e.value.detail


@pytest.mark.anyio
async def test_not_published_order_admin_bypass():
    assert await check_exists(OrderBase(
        type="comment",
        identifier=1,
        parents=dict(
            project="aaaa",
            site="aaaa",
            memory=1
        )
    ), "test", MockRepo(
        project_not_published=True,
        pid=False,
        site_not_published=True,
        sid=False,
        memory_not_published=True,
        mid=False,
        comment_not_published=True,
        cid=False,
        admin=True
    ), True) is None


@pytest.mark.anyio
async def test_ok():
    assert await check_exists(OrderBase(
        type="comment",
        identifier=1,
        parents=dict(
            project="aaaa",
            site="aaaa",
            memory=1
        )
    ), "test", MockRepo(
        project_not_published=False,
        pid=False,
        site_not_published=False,
        sid=False,
        memory_not_published=False,
        mid=False,
        comment_not_published=False,
        cid=False,
        admin=False
    ), True) is None
