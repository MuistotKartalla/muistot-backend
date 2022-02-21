import pytest
from headers import *

from utils import *


# noinspection DuplicatedCode
@pytest.fixture(name="setup")
async def setup(mock_request, db):
    pid = await create_project(db, mock_request)
    sid = await create_site(pid, db, mock_request)
    mid = await create_memory(pid, sid, db, mock_request)
    yield Setup(pid, sid, mid)
    await db.execute("DELETE FROM projects WHERE name = :project", dict(project=pid))


@pytest.mark.anyio
@pytest.mark.parametrize(
    "comment", ["Hello World öäå", "-äöäö.,mfaw®†¸é¸ß†˛†˛†", "a\x00"]
)
async def test_create(client, setup, credentials, auth, db, comment):
    r = client.post(
        COMMENTS.format(*setup), json=NewComment(comment=comment).dict(), headers=auth
    )
    if r.status_code != 201:
        c = await db.fetch_all("SELECT id, published FROM comments")
        m = await db.fetch_all("SELECT id, published FROM memories")
        s = await db.fetch_all("SELECT name, published FROM sites")
        p = await db.fetch_all("SELECT name, published FROM projects")
        u = await db.fetch_all("SELECT username FROM users")
        url = COMMENTS.format(*setup)
        assert r.status_code == 201, "\n-".join(repr(a) for a in [c, m, s, p, u, url])
    c = Comment(**client.get(r.headers[LOCATION]).json())
    assert c.user == credentials[0]
    assert c.comment == comment


@pytest.mark.anyio
async def test_fetch_all(client, setup, credentials, auth, db):
    comments = set()
    for i in range(0, 10):
        comment = genword(length=1000)
        comments.add(comment)
        client.post(
            COMMENTS.format(*setup),
            json=NewComment(comment=comment).dict(),
            headers=auth,
        )
    for c in Comments(**client.get(COMMENTS.format(*setup)).json()).items:
        assert c.comment in comments
        assert c.user == credentials[0]


@pytest.mark.anyio
async def test_delete(client, setup, auth, db):
    r = client.post(
        COMMENTS.format(*setup), json=NewComment(comment="test").dict(), headers=auth
    )
    assert r.status_code == 201
    _id = r.headers[LOCATION].removesuffix("/").split("/")[-1]
    assert (
            await db.fetch_val(f"SELECT EXISTS(SELECT 1 FROM comments WHERE id='{_id}')")
            == 1
    )
    assert client.delete(r.headers[LOCATION], headers=auth).status_code == 204
    assert (
            await db.fetch_val(f"SELECT EXISTS(SELECT 1 FROM comments WHERE id='{_id}')")
            == 0
    )


@pytest.mark.anyio
async def test_modify(client, setup, auth, db):
    r = client.post(
        COMMENTS.format(*setup), json=NewComment(comment="test").dict(), headers=auth
    )
    assert r.status_code == 201

    _id = r.headers[LOCATION].removesuffix("/").split("/")[-1]
    assert (
            await db.fetch_val(f"SELECT comment FROM comments WHERE id='{_id}'") == "test"
    )

    r = client.patch(
        r.headers[LOCATION], json=ModifiedComment(comment="test2").dict(), headers=auth
    )

    assert (
            await db.fetch_val(f"SELECT comment FROM comments WHERE id='{_id}'") == "test2"
    )

    assert r.status_code == 204
    assert (
            Comment(**client.get(r.headers[LOCATION], headers=auth).json()).comment
            == "test2"
    )
