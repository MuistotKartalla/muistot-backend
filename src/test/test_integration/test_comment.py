import pytest
from utils import *


# noinspection DuplicatedCode
@pytest.fixture(name="setup")
async def setup(mock_request, db):
    pid = await create_project(db, mock_request)
    sid = await create_site(pid, db, mock_request)
    mid = await create_memory(pid, sid, db, mock_request)
    yield Setup(pid, sid, mid)
    await db.execute("DELETE FROM projects WHERE name = :project", dict(project=pid))
