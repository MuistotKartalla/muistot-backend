import pytest
from fastapi import status
from headers import *

from utils import *


# noinspection DuplicatedCode
@pytest.fixture(name="setup")
async def setup(repo_config, db, username):
    pid = await create_project(db, repo_config, admins=[username])
    sid = await create_site(pid, db, repo_config)
    mid = await create_memory(pid, sid, db, repo_config)
    yield Setup(pid, sid, mid)
    await db.execute("DELETE FROM projects WHERE name = :project", dict(project=pid))


@pytest.fixture
async def admin(client, login):
    yield await authenticate(client, login[0], login[2])


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
    "comment", ["Hello World öäå", "-äöäö.,mfaw®†¸é¸ß†˛†˛†", "a\x00", " b b ", "a" * 2500]
)
@pytest.mark.anyio
async def test_create(client, setup, username, auth, comment, auto_publish):
    """Tests comment creation and whitespace stripping
    """
    r = await client.post(COMMENTS.format(*setup), json=NewComment(comment=comment).dict(), headers=auth)
    check_code(status.HTTP_201_CREATED, r)

    # Published
    c = to(Comment, await client.get(r.headers[LOCATION]))
    assert c.user == username
    assert c.comment == comment.strip()


@pytest.mark.anyio
async def test_create_unpublished(client, setup, auth):
    """Fresh comments are not auto published
    """
    r = await client.post(COMMENTS.format(*setup), json=NewComment(comment="a").dict(), headers=auth)
    check_code(status.HTTP_201_CREATED, r)
    check_code(status.HTTP_404_NOT_FOUND, await client.get(r.headers[LOCATION]))


@pytest.mark.anyio
async def test_fetch_all(client, setup, username, auth, auto_publish):
    """Create comments and ensure all get published
    """
    comments = set()
    for i in range(0, 10):
        comment = genword(length=1000)
        comments.add(comment)
        await client.post(
            COMMENTS.format(*setup),
            json=NewComment(comment=comment).dict(),
            headers=auth,
        )
    for c in to(Comments, await client.get(COMMENTS.format(*setup))).items:
        assert c.comment in comments
        assert c.user == username


@pytest.mark.anyio
async def test_delete(client, setup, auth, auto_publish):
    """Test comment deletion
    """
    r = await client.post(COMMENTS.format(*setup), json=NewComment(comment="test").dict(), headers=auth)
    loc = r.headers[LOCATION]

    check_code(status.HTTP_201_CREATED, r)
    check_code(status.HTTP_200_OK, await client.get(loc))
    check_code(status.HTTP_204_NO_CONTENT, await client.delete(loc, headers=auth))
    check_code(status.HTTP_404_NOT_FOUND, await client.get(loc, headers=auth))


@pytest.mark.anyio
async def test_delete_unpublished(client, setup, auth, auth2):
    """Test comment deletion failure on unpublished comment
    """
    r = await client.post(COMMENTS.format(*setup), json=NewComment(comment="unpublished").dict(), headers=auth)
    loc = r.headers[LOCATION]

    check_code(status.HTTP_201_CREATED, r)
    check_code(status.HTTP_404_NOT_FOUND, await client.get(loc))
    check_code(status.HTTP_404_NOT_FOUND, await client.delete(loc, headers=auth2))


@pytest.mark.anyio
async def test_delete_own_unpublished(client, setup, auth):
    """Test comment deletion on unpublished own comment
    """
    r = await client.post(COMMENTS.format(*setup), json=NewComment(comment="own-unpublished").dict(), headers=auth)
    loc = r.headers[LOCATION]

    check_code(status.HTTP_201_CREATED, r)
    check_code(status.HTTP_204_NO_CONTENT, await client.delete(loc, headers=auth))
    check_code(status.HTTP_404_NOT_FOUND, await client.get(loc, headers=auth))


@pytest.mark.anyio
async def test_modify(client, setup, auth):
    """User can modify their comments
    """
    r = await client.post(COMMENTS.format(*setup), json=NewComment(comment=" test1 ").dict(), headers=auth)
    loc = r.headers[LOCATION]
    check_code(status.HTTP_201_CREATED, r)

    c = to(Comment, await client.get(loc, headers=auth))
    assert c.comment == "test1"

    r = await client.patch(loc, json=ModifiedComment(comment="test2").dict(), headers=auth)
    check_code(status.HTTP_204_NO_CONTENT, r)

    c = to(Comment, await client.get(loc, headers=auth))
    assert c.comment == "test2"


@pytest.mark.anyio
async def test_get_own_unpublished(client, setup, auth2):
    """User can fetch their own unpublished comments
    """
    r = await client.post(COMMENTS.format(*setup), json=NewComment(comment="own comment").dict(), headers=auth2)
    loc = r.headers[LOCATION]
    check_code(status.HTTP_201_CREATED, r)

    r = await client.get(loc, headers=auth2)
    check_code(status.HTTP_200_OK, r)

    c = to(Comment, r)
    assert c.waiting_approval


@pytest.mark.anyio
async def test_admin_delete(client, setup, auth2, admin):
    """Admin can view and delete everything
    """
    r = await client.post(COMMENTS.format(*setup), json=NewComment(comment="someone elses comment").dict(),
                          headers=auth2)
    loc = r.headers[LOCATION]
    check_code(status.HTTP_201_CREATED, r)

    r = await client.get(loc, headers=admin)
    check_code(status.HTTP_200_OK, r)

    c = to(Comment, r)
    assert c.waiting_approval

    r = await client.delete(loc, headers=admin)
    check_code(status.HTTP_204_NO_CONTENT, r)

    check_code(status.HTTP_404_NOT_FOUND, await client.get(loc, headers=auth2))
    check_code(status.HTTP_404_NOT_FOUND, await client.get(loc, headers=admin))


@pytest.mark.anyio
async def test_collection_see_all(client, setup, auth2, admin):
    """Own creations are shown in collection for user.

    Admin sees all.
    """
    r = await client.post(COMMENTS.format(*setup), json=NewComment(comment="my comment").dict(), headers=auth2)
    comment_id = extract_id(r)

    assert all(map(lambda c: c.id != comment_id, to(Comments, await client.get(COMMENTS.format(*setup))).items))
    assert all(map(
        lambda c: c.id != comment_id and not c.waiting_approval,
        to(Comments, await client.get(COMMENTS.format(*setup))).items)
    )

    for a in (auth2, admin):
        assert any(map(
            lambda c: c.id == comment_id,
            to(Comments, await client.get(COMMENTS.format(*setup), headers=a)).items)
        )
        assert any(map(
            lambda c: c.id == comment_id and c.waiting_approval,
            to(Comments, await client.get(COMMENTS.format(*setup), headers=a)).items)
        )


@pytest.mark.anyio
async def test_admin_no_modify_but_delete(client, auth2, setup, admin, auto_publish):
    """Only posting user can modify

    Admin can delete
    """
    # Create
    r = await client.post(COMMENTS.format(*setup), json=NewComment(comment="someone elses comment").dict(),
                          headers=auth2)
    check_code(status.HTTP_201_CREATED, r)

    url = r.headers[LOCATION]

    r = await client.patch(url, json=dict(comment="ajdawijdijwaidwa"), headers=admin)
    check_code(status.HTTP_403_FORBIDDEN, r)

    r = await client.delete(url, headers=admin)
    check_code(status.HTTP_204_NO_CONTENT, r)


@pytest.mark.anyio
async def test_super_no_modify_but_delete(client, auth2, setup, superuser, auto_publish):
    """Only posting user can modify

    Super can delete
    """
    # Create
    r = await client.post(COMMENTS.format(*setup), json=NewComment(comment="someone elses comment").dict(),
                          headers=auth2)
    check_code(status.HTTP_201_CREATED, r)

    url = r.headers[LOCATION]

    r = await client.patch(url, json=dict(comment="adwwdadw"), headers=superuser)
    check_code(status.HTTP_403_FORBIDDEN, r)

    r = await client.delete(url, headers=superuser)
    check_code(status.HTTP_204_NO_CONTENT, r)


@pytest.mark.anyio
async def test_others_no_modify(client, auth2, setup, auth3, auto_publish):
    """Only posting user can modify
    """
    # Create
    r = await client.post(COMMENTS.format(*setup), json=NewComment(comment="someone elses comment").dict(),
                          headers=auth2)
    check_code(status.HTTP_201_CREATED, r)

    r = await client.patch(r.headers[LOCATION], json=dict(comment="dwjadwdiwidjiwowadä"), headers=auth3)
    check_code(status.HTTP_403_FORBIDDEN, r)
