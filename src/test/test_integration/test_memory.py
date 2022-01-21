import pytest

from utils import *


@pytest.fixture(name="setup")
async def setup(mock_request, db, login):
    pid = await create_project(db, mock_request, admins=[login[0]])
    sid = await create_site(pid, db, mock_request)
    yield Setup(pid, sid)
    await db.execute("DELETE FROM projects WHERE name = :project", dict(project=pid))


@pytest.mark.anyio
@pytest.mark.parametrize(
    "n", [
        1,
        7,
        1000
    ])
async def test_comment_count(client, db, setup, n, mock_request):
    mid = await create_memory(setup.project, setup.site, db, mock_request)
    setup.memory = mid
    cids = []

    for i in range(0, n):
        cids.append(str(await create_comment(setup.project, setup.site, mid, db, mock_request)))

    await db.execute(f"UPDATE comments SET published = 0 WHERE id IN ({','.join(cids)})")
    r = client.get(f'{setup.url}')
    assert r.status_code == 200, await db.fetch_all(
        "SELECT id, published FROM memories"
    )
    r = r.json()
    assert Memory(**r).comments_count == 0

    await db.execute(f"UPDATE comments SET published = 1 WHERE id IN ({','.join(cids)})")
    r = client.get(f'{setup.url}').json()
    assert Memory(**r).comments_count == n, setup.url


@pytest.mark.anyio
@pytest.mark.parametrize(
    "title,story", [
        (genword(length=10), genword(length=10)),
        (genword(length=10), None)
    ])
async def test_create_and_publish(client, db, setup, auth, login, title: str, story: str):
    from app.headers import LOCATION
    new_memory = NewMemory(
        title=title,
        story=story
    ).dict()
    r = client.post(f'{setup.url}/memories', json=new_memory, headers={})
    assert r.status_code == 403, "Created memory without auth"

    r = client.post(f'{setup.url}/memories', json=new_memory, headers=auth)
    assert r.status_code == 201, "Failed to make new memory"
    memory_url = r.headers[LOCATION]

    _id = memory_url.removesuffix('/').split('/')[-1]
    # un-publish
    await db.execute(
        "UPDATE memories SET published = 0 WHERE id = :id",
        values=dict(id=_id)
    )
    assert (await db.fetch_val("SELECT published FROM memories WHERE id = :id", values=dict(id=_id))) == 0

    print("Fetching unpublished")
    r = client.get(memory_url, headers=auth)
    assert r.status_code == 200, f"{repr(r.json())} - {memory_url} - {await db.fetch_all('SELECT * FROM memories')}"
    memory = Memory(**r.json())
    assert memory.waiting_approval == 1, f"Couldn't fetch unpublished - {await db.fetch_all('SELECT * FROM memories')}"

    await db.execute(f'UPDATE memories SET published = 1 WHERE id = :id', values=dict(id=memory.id))

    memory = Memory(**client.get(memory_url).json())

    assert memory.comments_count == 0
    assert memory.comments is None
    assert memory.user == login[0], "Wrong user"
    assert memory.title == title
    assert memory.story == story
    assert memory.waiting_approval is None, "Fetched published status unauthenticated"


@pytest.mark.anyio
async def test_modify(client, db, setup, auth, login):
    from app.headers import LOCATION
    memory = NewMemory(
        title=genword(length=100),
        story=genword(length=100)
    ).dict()
    r = client.post(f'{setup.url}/memories', json=memory, headers=auth)
    url = r.headers[LOCATION]

    for k, v in dict(title=200, story=1000).items():
        r = client.patch(url, json={k: genword(length=v)}, headers=auth)
        assert r.status_code == 200, await db.fetch_all("SELECT * FROM memories")
        assert len(client.get(url, headers=auth).json()[k]) == v, await db.fetch_all(
            "SELECT LENGTH(story) FROM memories"
        )
