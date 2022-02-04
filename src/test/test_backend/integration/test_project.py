import pytest
from fastapi import status
from fastapi.testclient import TestClient

from utils import *


@pytest.mark.anyio
async def test_invalid_project_406_edge_case(client: TestClient, login, db):
    """
    It is possible to insert bad values to the database manually.

    This tests they are correctly handled.
    """
    username, _, _ = login
    _id = await db.fetch_val(
        "INSERT INTO projects (name, published, default_language_id) VALUE (:pname, 1, 1) RETURNING id",
        values=dict(pname=username)
    )
    assert client.get(PROJECT.format(username)).status_code == status.HTTP_406_NOT_ACCEPTABLE
