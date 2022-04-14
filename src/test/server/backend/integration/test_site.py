import pytest
from fastapi import status
from headers import LOCATION
from muistot.backend.api.publish import PUPOrder

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

    name = genword(length=20)
    await db.execute(
        f"""
        INSERT INTO sites (name, published, project_id, location) 
        VALUE (:name, 1, (SELECT id FROM projects WHERE name = '{setup.project}'), POINT(10, 10))
        """,
        values=dict(name=name),
    )
    setup.site = name
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


def test_pap_modify(client, setup, pap, admin, auth2, superuser, auto_publish):
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


def test_bad_language(setup, client, admin):
    r = client.post(SITES.format(*setup), json=NewSite(
        id=genword(25),
        info=SiteInfo.construct(lang="az", name=genword(length=50)),
        location=Point(lon=10, lat=10)
    ).dict(), headers=admin)
    check_code(status.HTTP_406_NOT_ACCEPTABLE, r)


def test_own_site(setup, client, admin, auth2, auto_publish):
    _id, site = _create_site()
    r = client.post(SITES.format(*setup), json=site.dict(), headers=admin)
    check_code(status.HTTP_201_CREATED, r)
    site = to(Site, client.get(r.headers[LOCATION], headers=admin))
    assert site.own
    site = to(Site, client.get(r.headers[LOCATION], headers=auth2))
    assert not site.own


def test_modify_own_site(setup, client, auth2):
    _id, site = _create_site()
    r = client.post(SITES.format(*setup), json=site.dict(), headers=auth2)
    check_code(status.HTTP_201_CREATED, r)
    site.info.description = "awdwadawdiwuadiawuhjdiuawihdiuawhdiawuydawuiydhiuawydhuwhdwhdihawiudhawuidhuiawdhaw"
    r = client.patch(SITE.format(*setup, _id), json=site.dict(), headers=auth2)
    check_code(status.HTTP_204_NO_CONTENT, r)


def test_create_memory_for_site_not_change(setup, client, auth2, admin):
    _id, site = _create_site()
    r = client.post(SITES.format(*setup), json=site.dict(), headers=auth2)
    check_code(status.HTTP_201_CREATED, r)
    r = client.get(SITE.format(*setup, _id), headers=auth2)
    check_code(status.HTTP_200_OK, r)
    site = to(Site, r)
    assert site.waiting_approval

    client.post(
        PUBLISH,
        json=PUPOrder(parents={'project': setup.project}, identifier=_id, type='site').dict(),
        headers=admin
    )

    r = client.get(SITE.format(*setup, _id), headers=auth2)
    check_code(status.HTTP_200_OK, r)
    site = to(Site, r)
    assert not site.waiting_approval

    r = client.post(MEMORIES.format(*setup, _id), json=NewMemory(title="abcdefg").dict(), headers=auth2)
    check_code(status.HTTP_201_CREATED, r)

    r = client.get(SITE.format(*setup, _id), headers=auth2)
    check_code(status.HTTP_200_OK, r)
    site = to(Site, r)
    assert not site.waiting_approval


def test_fetch_all(client, setup, auto_publish, admin):
    for _ in range(0, 10):
        _id, site = _create_site()
        r = client.post(SITES.format(*setup), json=site.dict(), headers=admin)
        check_code(status.HTTP_201_CREATED, r)
    c = to(Sites, client.get(SITES.format(setup.project)))
    assert len(c.items) == 10


@pytest.mark.anyio
async def test_unpublished_project_site(db, setup, client, admin, auth2, auto_publish):
    _id, site = _create_site()
    r = client.post(SITES.format(*setup), json=site.dict(), headers=admin)
    check_code(status.HTTP_201_CREATED, r)

    await db.execute("UPDATE projects SET published = 0 WHERE name = :name", values=dict(name=setup.project))
    r = client.get(SITE.format(*setup, _id))
    assert r.status_code == status.HTTP_404_NOT_FOUND and "Project" in r.text


@pytest.mark.anyio
async def test_key_failure_project_site(db, setup, client, admin, auth2, auto_publish):
    await db.execute("SET FOREIGN_KEY_CHECKS=0")
    try:
        _id, site = _create_site()
        r = client.post(SITES.format(*setup), json=site.dict(), headers=admin)
        check_code(status.HTTP_201_CREATED, r)
        await db.execute("DELETE FROM projects WHERE name = :name", values=dict(name=setup.project))
        r = client.get(SITE.format(*setup, _id))
        assert r.status_code == status.HTTP_404_NOT_FOUND and "Project" in r.text
    finally:
        await db.execute("SET FOREIGN_KEY_CHECKS=1")


def test_site_patch_image(client, setup, db, auth, image, auto_publish):
    """Test image upload and delete
    """
    _id, site = _create_site()
    r = client.post(SITES.format(*setup), json=site.dict(), headers=auth)
    check_code(status.HTTP_201_CREATED, r)

    r = client.patch(SITE.format(*setup, _id), json=dict(image=f'data:image/png;base64,{image}'), headers=auth)
    check_code(status.HTTP_204_NO_CONTENT, r)

    # Check data
    r = client.get(IMAGE.format(to(Site, client.get(r.headers[LOCATION])).image))
    import base64
    assert image == base64.b64encode(r.content).decode('ascii')


def test_site_empty_modify_no_change(client, setup, db, auth, auto_publish):
    _id, site = _create_site()
    r = client.post(SITES.format(*setup), json=site.dict(), headers=auth)
    check_code(status.HTTP_201_CREATED, r)

    r = client.patch(SITE.format(*setup, _id), json=dict(), headers=auth)
    check_code(status.HTTP_304_NOT_MODIFIED, r)


def test_create_memory_for_site_has_image(setup, client, auth2, admin, image, auto_publish):
    """Test random assignment of image from memories
    """
    _id, site = _create_site()
    r = client.post(SITES.format(*setup), json=site.dict(), headers=auth2)
    check_code(status.HTTP_201_CREATED, r)

    r = client.post(MEMORIES.format(*setup, _id), json=NewMemory(title="abcdefg", image=image).dict(), headers=auth2)
    check_code(status.HTTP_201_CREATED, r)

    r = client.get(SITE.format(*setup, _id), headers=auth2)
    check_code(status.HTTP_200_OK, r)
    site = to(Site, r)
    assert site.image

    r = client.post(MEMORIES.format(*setup, _id), json=NewMemory(title="eddede", image=image).dict(), headers=auth2)
    check_code(status.HTTP_201_CREATED, r)

    r = client.get(SITE.format(*setup, _id), headers=auth2)
    check_code(status.HTTP_200_OK, r)
    site2 = to(Site, r)

    # Cached (5 min) should be same
    assert site.image == site2.image
