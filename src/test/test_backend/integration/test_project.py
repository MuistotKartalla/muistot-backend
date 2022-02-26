import pytest
from fastapi import status
from headers import LOCATION

from utils import *


@pytest.fixture
async def superuser(client, login, db, anyio_backend):
    await db.execute(
        """
        INSERT INTO superusers (user_id) SELECT id FROM users WHERE username = :user
        """,
        values=dict(user=login[0])
    )
    yield authenticate(client, login)
    await db.execute(
        """
        DELETE su FROM superusers su JOIN users u ON u.id = su.user_id WHERE u.username = :user
        """,
        values=dict(user=login[0])
    )


@pytest.fixture
async def pid(db, anyio_backend):
    from passlib.pwd import genword
    id_ = genword(length=25)
    yield id_
    await db.execute("DELETE FROM projects WHERE name = :id", values=dict(id=id_))


@pytest.mark.anyio
async def test_invalid_project_406_edge_case(client, login, db):
    """
    It is possible to insert bad values to the database manually.

    This tests they are correctly handled.
    """
    username, _, _ = login
    _id = await db.fetch_val(
        "INSERT INTO projects (name, published, default_language_id) VALUE (:pname, 1, 1) RETURNING id",
        values=dict(pname=username),
    )
    r = client.get(PROJECT.format(username))
    assert r.status_code == status.HTTP_406_NOT_ACCEPTABLE, r.text


def make_project(pid, client, superuser, **props):
    m = NewProject(
        id=pid,
        info=ProjectInfo(
            lang="en",
            name="Test Project ",
            abstract="Test Abstract",
            description="Test Description"
        ),
        **props
    )
    r = client.post(PROJECTS, json=m.dict(), headers=superuser)
    assert r.status_code == 201, r.text
    p = Project(**client.get(r.headers[LOCATION]).json())
    assert p.id == m.id
    assert p.info.name == m.info.name.strip()
    assert p.info.abstract == m.info.abstract
    assert p.info.description == m.info.description
    return p


def test_create(pid, client, superuser):
    make_project(pid, client, superuser)


def test_image(pid, client, superuser, image):
    p = make_project(
        pid,
        client,
        superuser,
        image=image,
    )
    assert p.image is not None
    r = client.patch(PROJECT.format(p.id), json={"image": None}, headers=superuser)
    assert r.status_code == 204, r.text
    assert Project(**client.get(r.headers[LOCATION]).json()).image is None, r.text
