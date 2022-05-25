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


def test_report_project_501(client, auth):
    order = ReportOrder(type="project", identifier="aaaa")
    r = client.post(REPORT, json=order.dict(), headers=auth)
    assert r.status_code == 501


@pytest.mark.anyio
async def test_report_site(client, auth, setup, auto_publish, db):
    order = ReportOrder(type="site", identifier=setup.site, parents=dict(project=setup.project))
    r = client.post(REPORT, json=order.dict(), headers=auth)
    assert r.status_code == 204, r.content
    assert await db.fetch_val("SELECT COUNT(*) FROM audit_sites") == 1


@pytest.mark.anyio
async def test_report_memory(client, auth, setup, auto_publish, db):
    order = ReportOrder(type="memory", identifier=setup.memory, parents=dict(
        project=setup.project,
        site=setup.site,
    ))
    r = client.post(REPORT, json=order.dict(), headers=auth)
    assert r.status_code == 204, r.content
    assert await db.fetch_val("SELECT COUNT(*) FROM audit_memories") == 1


@pytest.mark.anyio
async def test_report_comment(client, auth, setup, auto_publish, db):
    order = ReportOrder(type="comment", identifier=setup.comment, parents=dict(
        project=setup.project,
        site=setup.site,
        memory=setup.memory,
    ))
    r = client.post(REPORT, json=order.dict(), headers=auth)
    assert r.status_code == 204, r.content
    assert await db.fetch_val("SELECT COUNT(*) FROM audit_comments") == 1


def test_report_site_double(client, auth, setup, auto_publish):
    order = ReportOrder(type="site", identifier=setup.site, parents=dict(project=setup.project))
    r = client.post(REPORT, json=order.dict(), headers=auth)
    assert r.status_code == 204, r.content
    r = client.post(REPORT, json=order.dict(), headers=auth)
    assert r.status_code == 304, r.content
