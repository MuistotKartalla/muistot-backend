import pytest
from fastapi import status
from headers import LOCATION

from utils import *


@pytest.fixture(name="setup")
async def setup(repo_config, db, login):
    pid = await create_project(db, repo_config, admins=[login[0]])
    sid = await create_site(pid, db, repo_config)
    yield Setup(pid, sid)
    await db.execute("DELETE FROM projects WHERE name = :project", dict(project=pid))


@pytest.fixture
def admin(client, login):
    yield authenticate(client, login[0], login[2])


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

@pytest.mark.parametrize(
    "title,story",
    [(genword(length=10), genword(length=10)), (genword(length=10), None)],
)
def test_create_and_publish(client, setup, auth, title: str, story: str, auto_publish, username):
    """Create test
    """
    # Create
    m = NewMemory(title=title, story=story).dict()
    r = client.post(MEMORIES.format(*setup), json=m, headers=auth)
    check_code(status.HTTP_201_CREATED, r)

    # Get published
    r = client.get(r.headers[LOCATION])
    check_code(status.HTTP_200_OK, r)

    # Check props
    m = to(Memory, r)
    assert m.comments_count == 0
    assert m.comments is None
    assert m.user == username, "Wrong user"
    assert m.title == title
    assert m.story == story
    assert m.waiting_approval is None, "Fetched published status unauthenticated"


def test_create_no_auth(client, setup):
    """Only users can create
    """
    m = NewMemory(title="comment", story="no-auth").dict()
    r = client.post(MEMORIES.format(*setup), json=m, headers={})
    check_code(status.HTTP_401_UNAUTHORIZED, r)


def test_see_own_unpublished(client, auth, setup, username):
    """See own unpublished
    """
    # Create
    m = NewMemory(title="my comment").dict()
    r = client.post(MEMORIES.format(*setup), json=m, headers=auth)
    check_code(status.HTTP_201_CREATED, r)

    # Urls
    r = client.get(r.headers[LOCATION], headers=auth)
    check_code(status.HTTP_200_OK, r)

    m = to(Memory, r)
    assert m.waiting_approval == 1
    assert m.user == username


def test_unpublic_not_visible(client, auth, setup, username, auth2):
    """Can't see unpublished
    """
    # Create
    m = NewMemory(title="hidden comment").dict()
    r = client.post(MEMORIES.format(*setup), json=m, headers=auth)
    check_code(status.HTTP_201_CREATED, r)

    murl = r.headers[LOCATION]

    # Not visible to user
    r = client.get(murl, headers=auth2)
    check_code(status.HTTP_404_NOT_FOUND, r)

    # Not visible to no auth
    r = client.get(murl)
    check_code(status.HTTP_404_NOT_FOUND, r)


def test_see_published_without_auth(client, auth, setup, username, auto_publish):
    """Published is public
    """
    # Create
    m = NewMemory(title="cool comment").dict()
    r = client.post(MEMORIES.format(*setup), json=m, headers=auth)
    check_code(status.HTTP_201_CREATED, r)

    # Check
    r = client.get(r.headers[LOCATION])
    check_code(status.HTTP_200_OK, r)
    assert to(Memory, r).waiting_approval is None


def test_modify_full(client, setup, auth, login, auto_publish):
    """Full modify
    """
    m = NewMemory(title=genword(length=100), story=genword(length=100)).dict()
    r = client.post(MEMORIES.format(*setup), json=m, headers=auth)
    url = r.headers[LOCATION]

    m = dict(title="a", story="b")
    r = client.patch(url, json=m, headers=auth)
    check_code(status.HTTP_204_NO_CONTENT, r)

    mm = to(Memory, client.get(url))
    assert mm.dict(include=m.keys()) == m


def test_modify_one(client, setup, auth, login):
    """Modify one attr
    """
    title = genword(length=100)
    story = genword(length=1000)

    m = NewMemory(title=title).dict()
    r = client.post(MEMORIES.format(*setup), json=m, headers=auth)
    url = r.headers[LOCATION]

    m = dict(story=story)
    r = client.patch(url, json=m, headers=auth)
    check_code(status.HTTP_204_NO_CONTENT, r)

    r = client.get(url, headers=auth)
    m = to(Memory, r)
    assert m.story == story
    assert m.title == title


def test_delete_story(client, setup, auth, login):
    """Explicit null should delete story
    """
    title = genword(length=100)

    m = NewMemory(title=title, story=genword(length=100)).dict()
    r = client.post(MEMORIES.format(*setup), json=m, headers=auth)
    url = r.headers[LOCATION]

    m = dict(story=None)
    r = client.patch(url, json=m, headers=auth)
    check_code(status.HTTP_204_NO_CONTENT, r)

    r = client.get(url, headers=auth)
    m = to(Memory, r)
    assert m.story is None
    assert m.title == title


def test_admin_no_modify_but_delete(client, auth2, setup, admin, auto_publish):
    """Only posting user can modify

    Admin can delete
    """
    # Create
    m = NewMemory(title="no-admin").dict()
    r = client.post(MEMORIES.format(*setup), json=m, headers=auth2)
    check_code(status.HTTP_201_CREATED, r)

    url = r.headers[LOCATION]

    r = client.patch(url, json=dict(title="ajdawijdijwaidwa"), headers=admin)
    check_code(status.HTTP_403_FORBIDDEN, r)

    r = client.delete(url, headers=admin)
    check_code(status.HTTP_204_NO_CONTENT, r)


def test_super_no_modify_but_delete(client, auth2, setup, superuser, auto_publish):
    """Only posting user can modify

    Super can delete
    """
    # Create
    m = NewMemory(title="no-modify").dict()
    r = client.post(MEMORIES.format(*setup), json=m, headers=auth2)
    check_code(status.HTTP_201_CREATED, r)

    url = r.headers[LOCATION]

    r = client.patch(url, json=dict(title="adwwdadw"), headers=superuser)
    check_code(status.HTTP_403_FORBIDDEN, r)

    r = client.delete(url, headers=superuser)
    check_code(status.HTTP_204_NO_CONTENT, r)


def test_others_no_modify(client, auth2, setup, auth3, auto_publish):
    """Only posting user can modify
    """
    # Create
    m = NewMemory(title="no-others").dict()
    r = client.post(MEMORIES.format(*setup), json=m, headers=auth2)
    check_code(status.HTTP_201_CREATED, r)

    r = client.patch(r.headers[LOCATION], json=dict(title="dwjadwdiwidjiwowadä"), headers=auth3)
    check_code(status.HTTP_403_FORBIDDEN, r)


def test_image(client, auth, image, setup, auto_publish):
    """Images should work
    """
    # Create
    m = NewMemory(title="has image", image=image).dict()
    r = client.post(MEMORIES.format(*setup), json=m, headers=auth)
    check_code(status.HTTP_201_CREATED, r)

    r = client.get(r.headers[LOCATION])
    m = to(Memory, r)
    assert m.image is not None

    r = client.get(IMAGE.format(m.image))
    check_code(status.HTTP_200_OK, r)


def test_image_delete(client, auth, image, setup, auto_publish):
    """Image null should delete
    """
    # Create
    m = NewMemory(title="has image", image=image).dict()
    r = client.post(MEMORIES.format(*setup), json=m, headers=auth)
    check_code(status.HTTP_201_CREATED, r)

    url = r.headers[LOCATION]
    r = client.patch(url, json=dict(image=None), headers=auth)
    check_code(status.HTTP_204_NO_CONTENT, r)

    r = client.get(url)
    check_code(status.HTTP_200_OK, r)

    m = to(Memory, r)
    assert m.image is None
