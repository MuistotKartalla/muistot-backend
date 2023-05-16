import headers
import pytest
from fastapi import status

from muistot.backend.api.publish import PUPOrder
from utils import *


@pytest.fixture(name="setup")
async def setup(repo_config, db, username):
    pid = await create_project(db, repo_config, admins=[username])
    yield Setup(pid)
    await db.execute("DELETE FROM projects WHERE name = :project", dict(project=pid))


@pytest.fixture
async def admin(client, login, authenticate):
    yield await authenticate(login)


@pytest.fixture
async def pap(setup, db):
    await db.execute("UPDATE projects SET admin_posting = 1 WHERE name = :p", values=dict(p=setup.project))
    yield


async def _create_site(**kwargs):
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

@pytest.mark.anyio
async def test_create_and_publish(client, setup, db, admin, auth2):
    """Create and publish site
    """
    # Setup
    _id, site = await _create_site()

    # Create
    r = await client.post(SITES.format(*setup), json=site.dict(), headers=auth2)
    check_code(status.HTTP_201_CREATED, r)
    url = r.headers[LOCATION]

    # No-op
    r = await client.post(
        PUBLISH,
        json=PUPOrder(identifier=_id, type="site", publish=False, parents=dict(project=setup.project)).dict(),
        headers=admin,
    )
    check_code(status.HTTP_304_NOT_MODIFIED, r)
    assert to(Site, await client.get(url, headers=admin)).waiting_approval

    # Publish
    check_code(status.HTTP_204_NO_CONTENT, await client.post(
        PUBLISH,
        json=PUPOrder(identifier=_id, type="site", parents=dict(project=setup.project)).dict(),
        headers=admin,
    ))


@pytest.mark.anyio
async def test_modify_location(setup, client, auth, auto_publish):
    """Change site location
    """
    _id, site = await _create_site()

    r = await client.post(SITES.format(*setup), json=site.dict(), headers=auth)
    check_code(status.HTTP_201_CREATED, r)
    url = r.headers[LOCATION]

    r = await client.patch(url, json={"location": Point(lat=10, lon=20).dict()}, headers=auth)
    check_code(status.HTTP_204_NO_CONTENT, r)
    url = r.headers[LOCATION]

    assert to(Site, await client.get(url)).location == Point(lat=10, lon=20)


@pytest.mark.anyio
async def test_modify_location_same(setup, client, auth, auto_publish):
    """Change site location without actual change but return changed
    """
    _id, site = await _create_site()

    r = await client.post(SITES.format(*setup), json=site.dict(), headers=auth)
    check_code(status.HTTP_201_CREATED, r)
    url = r.headers[LOCATION]

    r = await client.patch(url, json={"location": site.location.dict()}, headers=auth)
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
    check_code(status.HTTP_406_NOT_ACCEPTABLE, await client.get(SITE.format(*setup)))


@pytest.mark.anyio
async def test_image(client, setup, db, auth, image, auto_publish):
    """Test image upload and delete
    """
    _id, site = await _create_site(image=image)
    r = await client.post(SITES.format(*setup), json=site.dict(), headers=auth)
    check_code(status.HTTP_201_CREATED, r)

    # Created
    url = r.headers[LOCATION]

    # Check not null
    s = to(Site, await client.get(url))
    assert s.image is not None

    # Found
    r = await client.get(IMAGE.format(s.image), follow_redirects=False)
    check_code(status.HTTP_200_OK, r)

    # Modify to null
    await client.patch(url, json={"image": None}, headers=auth)
    s = to(Site, await client.get(url))
    assert s.image is None


@pytest.mark.anyio
async def test_image_equals(client, setup, db, auth, image, auto_publish):
    """Test image data stays unchanged
    """
    _id, site = await _create_site(image=image)
    r = await client.post(SITES.format(*setup), json=site.dict(), headers=auth)
    check_code(status.HTTP_201_CREATED, r)

    # Check data
    r = await client.get(IMAGE.format(to(Site, await client.get(r.headers[LOCATION])).image))
    import base64
    assert image == base64.b64encode(r.content).decode('ascii')


@pytest.mark.anyio
async def test_pap_create(db, client, setup, pap, admin, auth2, superuser):
    """Only admins create
    """
    _id, site = await _create_site()

    r = await client.post(SITES.format(*setup), json=site.dict(), headers=auth2)
    check_code(status.HTTP_403_FORBIDDEN, r)

    r = await client.post(SITES.format(*setup), json=site.dict(), headers=admin)
    check_code(status.HTTP_201_CREATED, r)

    await db.execute("DELETE FROM sites WHERE name = :s", values=dict(s=site.id))

    r = await client.post(SITES.format(*setup), json=site.dict(), headers=superuser)
    check_code(status.HTTP_201_CREATED, r)


@pytest.mark.anyio
async def test_pap_modify(client, setup, pap, admin, auth2, superuser, auto_publish):
    """Only admins modify
    """
    _id, site = await _create_site()
    r = await client.post(SITES.format(*setup), json=site.dict(), headers=admin)
    check_code(status.HTTP_201_CREATED, r)

    loc = r.headers[LOCATION]

    r = await client.patch(loc, json=site.dict(), headers=auth2)
    check_code(status.HTTP_403_FORBIDDEN, r)

    site.location = Point(lat=20, lon=20)
    r = await client.patch(loc, json=site.dict(), headers=admin)
    check_code(status.HTTP_204_NO_CONTENT, r)

    site.location = Point(lat=30, lon=30)
    r = await client.patch(loc, json=site.dict(), headers=superuser)
    check_code(status.HTTP_204_NO_CONTENT, r)


@pytest.mark.anyio
async def test_bad_language(setup, client, admin):
    r = await client.post(SITES.format(*setup), json=NewSite(
        id=genword(25),
        info=SiteInfo.construct(lang="az", name=genword(length=50)),
        location=Point(lon=10, lat=10)
    ).dict(), headers=admin)
    check_code(status.HTTP_406_NOT_ACCEPTABLE, r)


@pytest.mark.anyio
async def test_own_site(setup, client, admin, auth2, auto_publish):
    _id, site = await _create_site()
    r = await client.post(SITES.format(*setup), json=site.dict(), headers=admin)
    check_code(status.HTTP_201_CREATED, r)
    site = to(Site, await client.get(r.headers[LOCATION], headers=admin))
    assert site.own
    site = to(Site, await client.get(r.headers[LOCATION], headers=auth2))
    assert not site.own


@pytest.mark.anyio
async def test_modify_own_site(setup, client, auth2):
    _id, site = await _create_site()
    r = await client.post(SITES.format(*setup), json=site.dict(), headers=auth2)
    check_code(status.HTTP_201_CREATED, r)
    site.info.description = "awdwadawdiwuadiawuhjdiuawihdiuawhdiawuydawuiydhiuawydhuwhdwhdihawiudhawuidhuiawdhaw"
    r = await client.patch(SITE.format(*setup, _id), json=site.dict(), headers=auth2)
    check_code(status.HTTP_204_NO_CONTENT, r)


@pytest.mark.anyio
async def test_create_memory_for_site_not_change(setup, client, auth2, admin):
    _id, site = await _create_site()
    r = await client.post(SITES.format(*setup), json=site.dict(), headers=auth2)
    check_code(status.HTTP_201_CREATED, r)
    r = await client.get(SITE.format(*setup, _id), headers=auth2)
    check_code(status.HTTP_200_OK, r)
    site = to(Site, r)
    assert site.waiting_approval

    await client.post(
        PUBLISH,
        json=PUPOrder(parents={'project': setup.project}, identifier=_id, type='site').dict(),
        headers=admin
    )

    r = await client.get(SITE.format(*setup, _id), headers=auth2)
    check_code(status.HTTP_200_OK, r)
    site = to(Site, r)
    assert not site.waiting_approval

    r = await client.post(MEMORIES.format(*setup, _id), json=NewMemory(title="abcdefg").dict(), headers=auth2)
    check_code(status.HTTP_201_CREATED, r)

    r = await client.get(SITE.format(*setup, _id), headers=auth2)
    check_code(status.HTTP_200_OK, r)
    site = to(Site, r)
    assert not site.waiting_approval


@pytest.mark.anyio
async def test_fetch_all(client, setup, auto_publish, admin):
    for _ in range(0, 10):
        _id, site = await _create_site()
        r = await client.post(SITES.format(*setup), json=site.dict(), headers=admin)
        check_code(status.HTTP_201_CREATED, r)
    c = to(Sites, await client.get(SITES.format(setup.project)))
    assert len(c.items) == 10


@pytest.mark.anyio
async def test_unpublished_project_site(db, setup, client, admin, auth2, auto_publish):
    _id, site = await _create_site()
    r = await client.post(SITES.format(*setup), json=site.dict(), headers=admin)
    check_code(status.HTTP_201_CREATED, r)

    await db.execute("UPDATE projects SET published = 0 WHERE name = :name", values=dict(name=setup.project))
    r = await client.get(SITE.format(*setup, _id))
    assert r.status_code == status.HTTP_404_NOT_FOUND and "Project" in r.text


@pytest.mark.anyio
async def test_key_failure_project_site(db, setup, client, admin, auth2, auto_publish):
    await db.execute("SET FOREIGN_KEY_CHECKS=0")
    try:
        _id, site = await _create_site()
        r = await client.post(SITES.format(*setup), json=site.dict(), headers=admin)
        check_code(status.HTTP_201_CREATED, r)
        await db.execute("DELETE FROM projects WHERE name = :name", values=dict(name=setup.project))
        r = await client.get(SITE.format(*setup, _id))
        assert r.status_code == status.HTTP_404_NOT_FOUND and "Project" in r.text
    finally:
        await db.execute("SET FOREIGN_KEY_CHECKS=1")


@pytest.mark.anyio
async def test_site_patch_image(client, setup, db, auth, image, auto_publish):
    """Test image upload and delete
    """
    _id, site = await _create_site()
    r = await client.post(SITES.format(*setup), json=site.dict(), headers=auth)
    check_code(status.HTTP_201_CREATED, r)

    r = await client.patch(SITE.format(*setup, _id), json=dict(image=f'data:image/png;base64,{image}'), headers=auth)
    check_code(status.HTTP_204_NO_CONTENT, r)

    # Check data
    r = await client.get(IMAGE.format(to(Site, await client.get(r.headers[LOCATION])).image))
    import base64
    assert image == base64.b64encode(r.content).decode('ascii')


@pytest.mark.anyio
async def test_site_empty_modify_no_change(client, setup, db, auth, auto_publish):
    _id, site = await _create_site()
    r = await client.post(SITES.format(*setup), json=site.dict(), headers=auth)
    check_code(status.HTTP_201_CREATED, r)

    r = await client.patch(SITE.format(*setup, _id), json=dict(), headers=auth)
    check_code(status.HTTP_304_NOT_MODIFIED, r)


@pytest.mark.anyio
async def test_create_memory_for_site_has_image(setup, client, auth2, admin, image, auto_publish):
    """Test random assignment of image from memories
    """
    _id, site = await _create_site()
    r = await client.post(SITES.format(*setup), json=site.dict(), headers=auth2)
    check_code(status.HTTP_201_CREATED, r)

    r = await client.post(MEMORIES.format(*setup, _id), json=NewMemory(title="abcdefg", image=image).dict(),
                          headers=auth2)
    check_code(status.HTTP_201_CREATED, r)

    r = await client.get(SITE.format(*setup, _id), headers=auth2)
    check_code(status.HTTP_200_OK, r)
    site = to(Site, r)
    assert site.image

    r = await client.post(MEMORIES.format(*setup, _id), json=NewMemory(title="eddede", image=image).dict(),
                          headers=auth2)
    check_code(status.HTTP_201_CREATED, r)

    r = await client.get(SITE.format(*setup, _id), headers=auth2)
    check_code(status.HTTP_200_OK, r)
    site2 = to(Site, r)
    assert site2.image is not None


@pytest.mark.anyio
async def test_create_site_non_default_locale_creates_default_placeholder(setup, client, admin, auto_publish):
    _id, site = await _create_site()
    site.info.lang = "en"
    r = await client.post(SITES.format(*setup), json=site.dict(), headers=admin)
    check_code(status.HTTP_201_CREATED, r)

    r = await client.get(SITE.format(*setup, _id), headers={headers.ACCEPT_LANGUAGE: "fi"})
    check_code(status.HTTP_200_OK, r)
    site = to(Site, r)
    assert site.info.abstract is None
    assert site.info.description is None
    assert site.info.name == site.info.name

    r = await client.get(SITE.format(*setup, _id), headers={headers.ACCEPT_LANGUAGE: "en"})
    check_code(status.HTTP_200_OK, r)
    site = to(Site, r)
    assert site.dict() == site.dict()


@pytest.mark.anyio
async def test_site_delete_own(client, setup, db, auth2):
    _id, site = await _create_site()
    r = await client.post(SITES.format(*setup), json=site.dict(), headers=auth2)
    check_code(status.HTTP_201_CREATED, r)

    r = await client.delete(SITE.format(*setup, _id), headers=auth2)
    check_code(status.HTTP_204_NO_CONTENT, r)

    assert await db.fetch_val(
        "SELECT NOT EXISTS(SELECT 1 FROM sites WHERE name = :id)",
        values=dict(id=_id)
    )


@pytest.mark.anyio
async def test_site_delete_other_admin(client, setup, db, auth2, admin):
    _id, site = await _create_site()
    r = await client.post(SITES.format(*setup), json=site.dict(), headers=auth2)
    check_code(status.HTTP_201_CREATED, r)

    r = await client.delete(SITE.format(*setup, _id), headers=admin)
    check_code(status.HTTP_204_NO_CONTENT, r)

    assert await db.fetch_val(
        "SELECT NOT EXISTS(SELECT 1 FROM sites WHERE name = :id)",
        values=dict(id=_id)
    )


@pytest.mark.anyio
async def test_site_localize_others_overwrite(client, setup, db, auth2, auth):
    _id, site = await _create_site()
    r = await client.post(SITES.format(*setup), json=site.dict(), headers=auth)
    check_code(status.HTTP_201_CREATED, r)

    info = ModifiedSite(info=SiteInfo(name="aaaa", description="a", abstract="a", lang="fi")).dict(exclude_unset=True)

    r = await client.patch(SITE.format(*setup, _id), json=info, headers=auth2)
    check_code(status.HTTP_404_NOT_FOUND, r)

    await db.execute("UPDATE sites SET published = 1 WHERE name = :id", values=dict(id=_id))

    r = await client.patch(SITE.format(*setup, _id), json=info, headers=auth2)
    check_code(status.HTTP_204_NO_CONTENT, r)

    creator = (await client.get("/me", headers=auth)).json()["username"]
    modifier = (await client.get("/me", headers=auth2)).json()["username"]

    assert await db.fetch_val(
        """
        SELECT u.username 
        FROM site_information si 
            JOIN sites s ON si.site_id = s.id 
                AND s.name = :id
            JOIN users u ON si.modifier_id = u.id
        """,
        values=dict(id=_id)
    ) == modifier

    r = await client.get(SITE.format(*setup, _id))
    check_code(status.HTTP_200_OK, r)
    s = to(Site, r)

    assert s.creator == creator
    assert s.modifier == modifier


@pytest.mark.anyio
async def test_site_fetch_by_distance(client, setup, db, auth, auto_publish):
    sites_data = []
    for i in range(0, 5):
        _id = genword(length=128)
        _site = NewSite(
            id=_id,
            info=SiteInfo(lang="fi", name=genword(length=50)),
            location=Point(lon=i * 10, lat=i * 10),
        )
        r = await client.post(SITES.format(*setup), json=_site.dict(), headers=auth)
        check_code(status.HTTP_201_CREATED, r)
        sites_data.append(_site.id)

    r = await client.get(SITES.format(*setup) + "?n=3&lat=10&lon=10")
    check_code(status.HTTP_200_OK, r)
    sites = to(Sites, r)

    assert len(sites.items) == 3
    a, b, c = map(lambda o: o.id, sites.items)

    assert a == sites_data[1]
    assert b == sites_data[0] or b == sites_data[2]
    assert c == sites_data[0] or c == sites_data[2]
    assert b != a != c


@pytest.mark.anyio
async def test_sites_include_memories(client, setup, db, auth, auto_publish, repo_config):
    _id, site = await _create_site()
    r = await client.post(SITES.format(*setup), json=site.dict(), headers=auth)
    check_code(status.HTTP_201_CREATED, r)

    await create_memory(setup.project, site.id, db, repo_config)

    r = await client.get(SITE.format(*setup, _id) + "?include_memories=true", headers=auth)
    check_code(status.HTTP_200_OK, r)
    s = to(Site, r)
    assert len(s.memories) == 1
    assert s.memories_count == 1


@pytest.mark.parametrize("q", [
    "?n=1",
    "?lat=10",
    "?lon=10",
    "?n=1&lat=10",
    "?n=1&lon=10",
    "?lat=10&lon=10",
    "?n=0&lat=10&lon=10",
    "?n=1&lat=-1&lon=10",
    "?n=1&lat=100&lon=10",
    "?n=1&lat=10&lon=-190",
    "?n=1&lat=10&lon=190",
])
@pytest.mark.anyio
async def test_site_fetch_by_distance_bad_params(client, setup, q):
    r = await client.get(SITES.format(*setup) + q)
    check_code(status.HTTP_422_UNPROCESSABLE_ENTITY, r)
