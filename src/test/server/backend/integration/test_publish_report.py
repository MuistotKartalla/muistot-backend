import pytest
from muistot.backend.api.publish import *

from utils import *


@pytest.fixture(name="setup")
async def setup(repo_config, db, login):
    pid = await create_project(db, repo_config)
    sid = await create_site(pid, db, repo_config)
    yield Setup(pid, sid)
    await db.execute("DELETE FROM projects WHERE name = :project", dict(project=pid))


def test_report_project_501(client, auth):
    order = ReportOrder(type="project", identifier="aaaa")
    r = client.post(REPORT, json=order.dict(), headers=auth)
    assert r.status_code == 501


def test_report_site(client, auth, setup, auto_publish):
    order = ReportOrder(type="site", identifier=setup.site, parents=dict(project=setup.project))
    r = client.post(REPORT, json=order.dict(), headers=auth)
    assert r.status_code == 204, r.content


def test_report_site_double(client, auth, setup, auto_publish):
    order = ReportOrder(type="site", identifier=setup.site, parents=dict(project=setup.project))
    r = client.post(REPORT, json=order.dict(), headers=auth)
    assert r.status_code == 204, r.content
    r = client.post(REPORT, json=order.dict(), headers=auth)
    assert r.status_code == 304, r.content
