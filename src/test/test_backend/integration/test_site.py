import pytest
from fastapi import status
from headers import LOCATION
from muistoja.backend.api.publish import PUPOrder

from utils import *


@pytest.fixture(name="setup")
async def setup(repo_config, db, username, anyio_backend):
    pid = await create_project(db, repo_config, admins=[username])
    yield Setup(pid)
    await db.execute("DELETE FROM projects WHERE name = :project", dict(project=pid))


@pytest.fixture
def admin(client, login):
    yield authenticate(client, login[0], login[2])


@pytest.fixture
async def pap(setup, db, anyio_backend):
    await db.execute("UPDATE projects SET admin_posting = 1 WHERE name = :p", values=dict(p=setup.project))
    yield


def _create_site(**kwargs):
    _id = genword(length=128)
    site = NewSite(
        id=_id,
        info=SiteInfo(lang="fi", name=genword(length=50)),
        location=Point(lon=10, lat=10),
        **kwargs
    )
    return _id, site


#        ___           ___           ___           ___           ___
#       /\  \         /\  \         /\  \         /\  \         /\  \
#      /::\  \        \:\  \       /::\  \       /::\  \        \:\  \
#     /:/\ \  \        \:\  \     /:/\:\  \     /:/\:\  \        \:\  \
#    _\:\~\ \  \       /::\  \   /::\~\:\  \   /::\~\:\  \       /::\  \
#   /\ \:\ \ \__\     /:/\:\__\ /:/\:\ \:\__\ /:/\:\ \:\__\     /:/\:\__\
#   \:\ \:\ \/__/    /:/  \/__/ \/__\:\/:/  / \/_|::\/:/  /    /:/  \/__/
#    \:\ \:\__\     /:/  /           \::/  /     |:|::/  /    /:/  /
#     \:\/:/  /     \/__/            /:/  /      |:|\/__/     \/__/
#      \::/  /                      /:/  /       |:|  |
#       \/__/                       \/__/         \|__|

def test_create_and_publish(client, setup, db, admin, auth2):
    """Create and publish site
    """
    # Setup
    _id, site = _create_site()

    # Create
    r = client.post(SITES.format(*setup), json=site.dict(), headers=auth2)
    check_code(status.HTTP_201_CREATED, r)
    url = r.headers[LOCATION]

    # No-op
    r = client.post(
        PUBLISH,
        json=PUPOrder(identifier=_id, type="site", publish=False, parents=dict(project=setup.project)).dict(),
        headers=admin,
    )
    check_code(status.HTTP_304_NOT_MODIFIED, r)
    assert to(Site, client.get(url, headers=admin)).waiting_approval

    # Publish
    check_code(status.HTTP_204_NO_CONTENT, client.post(
        PUBLISH,
        json=PUPOrder(identifier=_id, type="site", parents=dict(project=setup.project)).dict(),
        headers=admin,
    ))


def test_modify_location(setup, client, auth, auto_publish):
    """Change site location
    """
    _id, site = _create_site()

    r = client.post(SITES.format(*setup), json=site.dict(), headers=auth)
    check_code(status.HTTP_201_CREATED, r)
    url = r.headers[LOCATION]

    r = client.patch(url, json={"location": Point(lat=10, lon=20).dict()}, headers=auth)
    check_code(status.HTTP_204_NO_CONTENT, r)
    url = r.headers[LOCATION]

    assert to(Site, client.get(url)).location == Point(lat=10, lon=20)


def test_modify_location_same(setup, client, auth, auto_publish):
    """Change site location without actual change but return changed

    TODO: Change this to check for 304 when caching is enabled
    """
    _id, site = _create_site()

    r = client.post(SITES.format(*setup), json=site.dict(), headers=auth)
    check_code(status.HTTP_201_CREATED, r)
    url = r.headers[LOCATION]

    r = client.patch(url, json={"location": site.location.dict()}, headers=auth)
    check_code(status.HTTP_204_NO_CONTENT, r)


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
        VALUE (:name, 1, (SELECT id FROM projects WHERE name = '{setup.project}'), POINT(10, 10))
        """,
        values=dict(name=username),
    )
    setup.site = username
    check_code(status.HTTP_406_NOT_ACCEPTABLE, client.get(SITE.format(*setup)))


def test_image(client, setup, db, auth, image, auto_publish):
    """Test image upload and delete
    """
    _id, site = _create_site(image=image)
    r = client.post(SITES.format(*setup), json=site.dict(), headers=auth)
    check_code(status.HTTP_201_CREATED, r)

    # Created
    url = r.headers[LOCATION]

    # Check not null
    s = to(Site, client.get(url))
    assert s.image is not None
    print(s.image)

    # Found
    r = client.get(IMAGE.format(s.image), allow_redirects=False)
    check_code(status.HTTP_200_OK, r)

    # Modify to null
    client.patch(url, json={"image": None}, headers=auth)
    s = to(Site, client.get(url))
    assert s.image is None


def test_image_equals(client, setup, db, auth, image, auto_publish):
    """Test image data stays unchanged
    """
    _id, site = _create_site(image=image)
    r = client.post(SITES.format(*setup), json=site.dict(), headers=auth)
    check_code(status.HTTP_201_CREATED, r)

    # Check data
    r = client.get(IMAGE.format(to(Site, client.get(r.headers[LOCATION])).image))
    import base64
    assert image == base64.b64encode(r.content).decode('ascii')


@pytest.mark.anyio
async def test_pap_create(db, client, setup, pap, admin, auth2, superuser):
    """Only admins create
    """
    _id, site = _create_site()

    r = client.post(SITES.format(*setup), json=site.dict(), headers=auth2)
    check_code(status.HTTP_403_FORBIDDEN, r)

    r = client.post(SITES.format(*setup), json=site.dict(), headers=admin)
    check_code(status.HTTP_201_CREATED, r)

    await db.execute("DELETE FROM sites WHERE name = :s", values=dict(s=site.id))

    r = client.post(SITES.format(*setup), json=site.dict(), headers=superuser)
    check_code(status.HTTP_201_CREATED, r)


def test_pap_modify(client, setup, pap, admin, auth2, superuser):
    """Only admins modify
    """
    _id, site = _create_site()
    r = client.post(SITES.format(*setup), json=site.dict(), headers=admin)
    check_code(status.HTTP_201_CREATED, r)

    loc = r.headers[LOCATION]

    r = client.patch(loc, json=site.dict(), headers=auth2)
    check_code(status.HTTP_403_FORBIDDEN, r)

    site.location = Point(lat=20, lon=20)
    r = client.patch(loc, json=site.dict(), headers=admin)
    check_code(status.HTTP_204_NO_CONTENT, r)

    site.location = Point(lat=30, lon=30)
    r = client.patch(loc, json=site.dict(), headers=superuser)
    check_code(status.HTTP_204_NO_CONTENT, r)
