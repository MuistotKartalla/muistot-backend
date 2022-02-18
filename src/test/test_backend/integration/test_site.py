import pytest
from muistoja.backend.api.admin import PUPOrder
from headers import LOCATION

from utils import *


@pytest.mark.anyio
@pytest.fixture(name="setup")
async def setup(mock_request, db, login):
    pid = await create_project(db, mock_request, admins=[login[0]])
    yield Setup(pid)
    await db.execute("DELETE FROM projects WHERE name = :project", dict(project=pid))


@pytest.mark.anyio
async def test_create_and_publish(client, setup, db, login):
    auth = authenticate(client, login)
    _id = genword(length=128)
    site = NewSite(
        id=_id,
        info=SiteInfo(lang='fi', name=genword(length=50)),
        location=Point(lon=10, lat=10)
    )

    # create
    r = client.post(f'{setup.url}/sites', json=site.dict(), headers=auth)
    assert r.status_code == 201, r.text
    url = r.headers[LOCATION]

    # un-publish
    r = client.post(f'{setup.url}/admin/publish', json=PUPOrder(
        identifier=_id,
        type='site',
        publish=False
    ).dict(), headers=auth)
    assert r.status_code in {204, 304}, r.text

    assert Site(**client.get(url, headers=auth).json()).waiting_approval

    # publish
    assert client.post(f'{setup.url}/admin/publish', json=PUPOrder(
        identifier=_id,
        type='site'
    ).dict(), headers=auth).status_code == 204


@pytest.mark.anyio
async def test_invalid_site_406_edge_case(client, login, db, setup):
    """
    It is possible to insert bad values to the database manually.

    This tests they are correctly handled.
    """
    from fastapi import status
    username, _, _ = login
    await db.execute(
        f"""
        INSERT INTO sites (name, published, project_id, location) 
        VALUE (:name, 1, (SELECT id FROM projects WHERE name = "{setup.project}"), POINT(10, 10))
        """,
        values=dict(name=username)
    )
    setup.site = username
    assert client.get(setup.url).status_code == status.HTTP_406_NOT_ACCEPTABLE
