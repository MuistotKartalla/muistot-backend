from functools import partial

import pytest

from utils import *


@pytest.fixture(name="setup")
async def setup(repo_config, db, login):
    pid = await create_project(db, repo_config, admins=[login[0]])
    sid = await create_site(pid, db, repo_config)
    yield Setup(pid, sid)
    await db.execute("DELETE FROM projects WHERE name = :project", dict(project=pid))


async def _check(n: int, url: str, table: str, identifier: str, model, db, client, creator):
    ids = []
    for i in range(0, n):
        ids.append(await creator())

    ids = list(map(lambda o: f"'{o}'" if isinstance(o, str) else f"{o}", ids))

    await db.execute(f"UPDATE {table} SET published = 0 WHERE {identifier} IN ({','.join(ids)})")
    assert getattr(to(model, client.get(url)), f"{table}_count") == 0

    await db.execute(f"UPDATE {table} SET published = 1 WHERE {identifier} IN ({','.join(ids)})")
    assert getattr(to(model, client.get(url)), f"{table}_count") == n


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
@pytest.mark.parametrize("n", [1, 7, 100])
async def test_comment_count(client, db, setup, n, repo_config):
    """Test that comment count shows up correctly
    """
    mid = await create_memory(setup.project, setup.site, db, repo_config)
    setup.memory = mid

    await _check(
        n,
        MEMORY.format(*setup),
        "comments",
        "id",
        Memory,
        db,
        client,
        partial(create_comment, setup.project, setup.site, mid, db, repo_config),
    )


@pytest.mark.anyio
@pytest.mark.parametrize("n", [1, 7, 100])
async def test_site_count(client, db, setup, n, repo_config):
    """Test that site count shows up correctly
    """
    await db.execute("UPDATE sites SET published = 0 WHERE name = :s", values=dict(s=setup.site))
    await _check(
        n,
        PROJECT.format(setup.project),
        "sites",
        "name",
        Project,
        db,
        client,
        partial(create_site, setup.project, db, repo_config),
    )


@pytest.mark.anyio
@pytest.mark.parametrize("n", [1, 7, 100])
async def test_memory_count(client, db, setup, n, repo_config):
    """Test that memory count shows up correctly
    """
    await db.execute("UPDATE sites SET published = 1 WHERE name = :s", values=dict(s=setup.site))
    await _check(
        n,
        SITE.format(setup.project, setup.site),
        "memories",
        "id",
        Site,
        db,
        client,
        partial(create_memory, setup.project, setup.site, db, repo_config),
    )
