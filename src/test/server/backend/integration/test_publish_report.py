import pytest
from muistot.backend.api.publish import *

from utils import *


@pytest.fixture(name="setup")
async def setup(repo_config, db, login):
    pid = await create_project(db, repo_config)
    sid = await create_site(pid, db, repo_config)
    mid = await create_memory(pid, sid, db, repo_config)
    cid = await create_comment(pid, sid, mid, db, repo_config)
    yield Setup(pid, sid, mid, cid)
    await db.execute("DELETE FROM projects WHERE name = :project", dict(project=pid))


@pytest.fixture
async def admin(setup, db, login, client):
    await db.execute(
        """
        INSERT INTO project_admins (project_id, user_id)
        SELECT p.id, u.id FROM projects p JOIN users u ON u.username = :user WHERE p.name = :p
        """,
        values=dict(p=setup.project, user=login[0])
    )
    yield await authenticate(client, login[0], login[2])


@pytest.mark.anyio
async def test_report_project_501(client, auth):
    order = ReportOrder(type="project", identifier="aaaa")
    r = await client.post(REPORT, json=order.dict(), headers=auth)
    assert r.status_code == 501


@pytest.mark.anyio
async def test_report_site(client, auth, setup, auto_publish, db):
    assert await db.fetch_val("SELECT COUNT(*) FROM audit_sites") == 0
    order = ReportOrder(type="site", identifier=setup.site, parents=dict(project=setup.project))
    r = await client.post(REPORT, json=order.dict(), headers=auth)
    assert r.status_code == 204, r.content
    assert await db.fetch_val("SELECT COUNT(*) FROM audit_sites") == 1


@pytest.mark.anyio
async def test_report_memory(client, auth, setup, auto_publish, db):
    assert await db.fetch_val("SELECT COUNT(*) FROM audit_memories") == 0
    order = ReportOrder(type="memory", identifier=setup.memory, parents=dict(
        project=setup.project,
        site=setup.site,
    ))
    r = await client.post(REPORT, json=order.dict(), headers=auth)
    assert r.status_code == 204, r.content
    assert await db.fetch_val("SELECT COUNT(*) FROM audit_memories") == 1


@pytest.mark.anyio
async def test_report_comment(client, auth, setup, auto_publish, db):
    assert await db.fetch_val("SELECT COUNT(*) FROM audit_comments") == 0
    order = ReportOrder(type="comment", identifier=setup.comment, parents=dict(
        project=setup.project,
        site=setup.site,
        memory=setup.memory,
    ))
    r = await client.post(REPORT, json=order.dict(), headers=auth)
    assert r.status_code == 204, r.content
    assert await db.fetch_val("SELECT COUNT(*) FROM audit_comments") == 1


@pytest.mark.anyio
async def test_report_site_double(client, auth, setup, auto_publish):
    order = ReportOrder(type="site", identifier=setup.site, parents=dict(project=setup.project))
    r = await client.post(REPORT, json=order.dict(), headers=auth)
    assert r.status_code == 204, r.content
    r = await client.post(REPORT, json=order.dict(), headers=auth)
    assert r.status_code == 304, r.content


@pytest.mark.anyio
async def test_report_site_resource(client, auth, setup, auto_publish, db):
    assert await db.fetch_val("SELECT COUNT(*) FROM audit_sites") == 0
    r = await client.put(REPORT_SITE.format(
        setup.project,
        setup.site,
    ), headers=auth)
    assert r.status_code == 204, r.content
    r = await client.put(REPORT_SITE.format(
        setup.project,
        setup.site,
    ), headers=auth)
    assert r.status_code == 204, r.content
    assert await db.fetch_val("SELECT COUNT(*) FROM audit_sites") == 1


@pytest.mark.anyio
async def test_report_memory_resource(client, auth, setup, auto_publish, db):
    assert await db.fetch_val("SELECT COUNT(*) FROM audit_memories") == 0
    r = await client.put(REPORT_MEMORY.format(
        setup.project,
        setup.site,
        setup.memory,
    ), headers=auth)
    assert r.status_code == 204, r.content
    r = await client.put(REPORT_MEMORY.format(
        setup.project,
        setup.site,
        setup.memory,
    ), headers=auth)
    assert r.status_code == 204, r.content
    assert await db.fetch_val("SELECT COUNT(*) FROM audit_memories") == 1


@pytest.mark.anyio
async def test_report_comment_resource(client, auth, setup, auto_publish, db):
    assert await db.fetch_val("SELECT COUNT(*) FROM audit_comments") == 0
    r = await client.put(REPORT_COMMENT.format(
        setup.project,
        setup.site,
        setup.memory,
        setup.comment,
    ), headers=auth)
    assert r.status_code == 204, r.content
    r = await client.put(REPORT_COMMENT.format(
        setup.project,
        setup.site,
        setup.memory,
        setup.comment,
    ), headers=auth)
    assert r.status_code == 204, r.content
    assert await db.fetch_val("SELECT COUNT(*) FROM audit_comments") == 1


@pytest.mark.anyio
async def test_publish_comment_resource(client, admin, setup, auto_publish, db):
    r = await client.post(PUBLISH_COMMENT.format(
        setup.project,
        setup.site,
        setup.memory,
        setup.comment,
        False,
    ), headers=admin)
    assert r.status_code == 204, r.content

    r = await client.post(PUBLISH_COMMENT.format(
        setup.project,
        setup.site,
        setup.memory,
        setup.comment,
        False,
    ), headers=admin)
    assert r.status_code == 304, r.content

    r = await client.get(COMMENT.format(setup.project, setup.site, setup.memory, setup.comment))
    assert r.status_code == 404, r.content

    r = await client.post(PUBLISH_COMMENT.format(
        setup.project,
        setup.site,
        setup.memory,
        setup.comment,
        True,
    ), headers=admin)
    assert r.status_code == 204, r.content

    r = await client.get(COMMENT.format(setup.project, setup.site, setup.memory, setup.comment))
    assert r.status_code == 200, r.content


@pytest.mark.anyio
async def test_publish_memory_resource(client, admin, setup, auto_publish, db):
    r = await client.post(PUBLISH_MEMORY.format(
        setup.project,
        setup.site,
        setup.memory,
        False,
    ), headers=admin)
    assert r.status_code == 204, r.content

    r = await client.post(PUBLISH_MEMORY.format(
        setup.project,
        setup.site,
        setup.memory,
        False,
    ), headers=admin)
    assert r.status_code == 304, r.content

    r = await client.get(MEMORY.format(setup.project, setup.site, setup.memory))
    assert r.status_code == 404, r.content

    r = await client.post(PUBLISH_MEMORY.format(
        setup.project,
        setup.site,
        setup.memory,
        True,
    ), headers=admin)
    assert r.status_code == 204, r.content

    r = await client.get(MEMORY.format(setup.project, setup.site, setup.memory))
    assert r.status_code == 200, r.content


@pytest.mark.anyio
async def test_publish_site_resource(client, admin, setup, auto_publish, db):
    r = await client.post(PUBLISH_SITE.format(
        setup.project,
        setup.site,
        False,
    ), headers=admin)
    assert r.status_code == 204, r.content

    r = await client.post(PUBLISH_SITE.format(
        setup.project,
        setup.site,
        False,
    ), headers=admin)
    assert r.status_code == 304, r.content

    r = await client.get(SITE.format(setup.project, setup.site))
    assert r.status_code == 404, r.content

    r = await client.post(PUBLISH_SITE.format(
        setup.project,
        setup.site,
        True,
    ), headers=admin)
    assert r.status_code == 204, r.content

    r = await client.get(SITE.format(setup.project, setup.site))
    assert r.status_code == 200, r.content
