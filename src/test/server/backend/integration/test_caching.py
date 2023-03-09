import pytest
from fastapi import status

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
def get_len(using_cache):
    yield lambda: len(list(using_cache.keys("*")))


@pytest.mark.anyio
async def test_projects_cache(setup, superuser, client, using_cache, get_len):
    start = get_len()
    expected = 2

    r = await client.get(PROJECT.format(setup.project))
    check_code(status.HTTP_200_OK, r)
    p = to(Project, r)
    assert get_len() - start == expected  # Added one key and One set

    r = await client.get(PROJECT.format(setup.project))
    check_code(status.HTTP_200_OK, r)
    assert p == to(Project, r)
    assert get_len() - start == expected  # No change

    r = await client.get(PROJECTS)
    check_code(status.HTTP_200_OK, r)
    expected += 1
    assert get_len() - start == expected  # Added one key and One set member

    r = await client.post(PUBLISH_PROJECT.format(setup.project, False))
    check_code(status.HTTP_401_UNAUTHORIZED, r)
    assert get_len() - start == expected  # No change

    r = await client.post(PUBLISH_PROJECT.format(setup.project, False), headers=superuser)
    check_code(status.HTTP_204_NO_CONTENT, r)
    assert get_len() == start  # Both keys deleted and set cleared


@pytest.mark.anyio
async def test_sites_evict_projects(setup, superuser, client, using_cache, get_len):
    start = get_len()
    expected = 2

    r = await client.get(PROJECT.format(setup.project))
    check_code(status.HTTP_200_OK, r)
    p = to(Project, r)
    assert p.sites_count >= 1
    assert get_len() - start == expected  # Added one key and One set

    r = await client.get(SITES.format(setup.project))
    check_code(status.HTTP_200_OK, r)
    expected += 2
    assert get_len() - start == expected  # Added one key and One set

    r = await client.post(PUBLISH_SITE.format(setup.project, setup.site, False), headers=superuser)
    check_code(status.HTTP_204_NO_CONTENT, r)
    assert get_len() == start  # Evicted project and Site Caches


@pytest.mark.anyio
async def test_memories_evict_sites(setup, superuser, client, using_cache, get_len):
    start = get_len()
    expected = 2

    r = await client.get(PROJECT.format(setup.project))
    check_code(status.HTTP_200_OK, r)
    assert get_len() - start == expected  # Added one key and One set

    r = await client.get(SITES.format(setup.project))
    check_code(status.HTTP_200_OK, r)
    expected += 2
    assert get_len() - start == expected  # Added one key and One set

    r = await client.post(PUBLISH_MEMORY.format(setup.project, setup.site, setup.memory, False), headers=superuser)
    check_code(status.HTTP_204_NO_CONTENT, r)
    expected -= 2
    assert get_len() - start == expected  # Evicted and Site Caches but not project


@pytest.mark.anyio
async def test_same_scopes_cache(setup, users, client, using_cache, get_len, superuser):
    start = get_len()
    expected = 2

    auth1 = await authenticate(client, users[1].username, users[1].password)
    auth2 = await authenticate(client, users[2].username, users[2].password)

    r = await client.get(PROJECT.format(setup.project), headers=auth1)
    check_code(status.HTTP_200_OK, r)
    assert get_len() - start == expected  # Added one key and One set

    r = await client.get(PROJECT.format(setup.project), headers=auth2)
    check_code(status.HTTP_200_OK, r)
    assert get_len() - start == expected  # Nothing added with identical scopes

    r = await client.get(PROJECT.format(setup.project), headers=superuser)
    check_code(status.HTTP_200_OK, r)
    expected += 1
    assert get_len() - start == expected  # Added one key


@pytest.mark.anyio
async def test_cache_is_faster(setup, client, using_cache, db, repo_config, superuser, auth2, users):
    for _ in range(0, 10):
        await create_site(setup.project, db, repo_config)

    old = client.app.state.FastStorage.redis

    class NullCache:

        def __getattribute__(self, item):
            return lambda *_, **__: None

    client.app.state.FastStorage.redis = NullCache()

    await db.execute(
        """
        INSERT INTO project_admins (project_id, user_id) 
        SELECT p.id, u.id FROM users u JOIN projects p ON p.name = :name WHERE u.username = :user
        """,
        values=dict(user=users[2].username, name=setup.project)
    )
    auth3 = await authenticate(client, users[2].username, users[2].password)

    import time

    headers = [superuser, auth2, auth3]

    async def do_test():
        start = time.time()
        for i in range(0, 10):
            r = await client.get(SITES.format(setup.project), headers=headers[i % 3])
            check_code(status.HTTP_200_OK, r)
        return time.time() - start

    try:
        no_cache = await do_test()
    finally:
        client.app.state.FastStorage.redis = old

    with_cache = await do_test()

    assert with_cache < no_cache
