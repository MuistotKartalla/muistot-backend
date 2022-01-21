import pytest

from utils import *


@pytest.mark.anyio
@pytest.fixture(name="setup")
async def setup(mock_request, db, login):
    pid = await create_project(db, mock_request, admins=[login[0]])
    yield Setup(pid)
    await db.execute("DELETE FROM projects WHERE name = :project", dict(project=pid))


@pytest.mark.anyio
async def test_create_and_publish(client, setup, db, auth):
    from app.headers import LOCATION
    from app.api.admin import PUPOrder

    _id = genword(length=128)
    site = NewSite(
        id=_id,
        info=SiteInfo(lang='fi', name=genword(length=50)),
        location=Point(lon=10, lat=10)
    )

    # create
    r = client.post(f'{setup.url}/sites', json=site.dict(), headers=auth)
    assert r.status_code == 201
    url = r.headers[LOCATION]

    # un-publish
    assert client.post(f'{setup.url}/admin/publish', json=PUPOrder(
        identifier=_id,
        type='site',
        publish=False
    ).dict(), headers=auth).status_code in {204, 304}, setup.url

    assert Site(**client.get(url, headers=auth).json()).waiting_approval

    # publish
    assert client.post(f'{setup.url}/admin/publish', json=PUPOrder(
        identifier=_id,
        type='site'
    ).dict(), headers=auth).status_code == 204
