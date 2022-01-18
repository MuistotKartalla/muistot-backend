import pytest
from utils import *


@pytest.mark.anyio
@pytest.fixture(name="setup")
async def setup(mock_request, db):
    pid = await create_project(db, mock_request)
    yield Setup(pid)
    await db.execute("DELETE FROM projects WHERE name = :project", dict(project=pid))
