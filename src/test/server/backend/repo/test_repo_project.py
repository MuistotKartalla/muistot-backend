import datetime

import pytest
from fastapi import Request, HTTPException, status

from muistot.backend.models import ModifiedProject, ProjectContact, NewProject, ProjectInfo
from muistot.backend.repos import ProjectRepo
from muistot.security import User, scopes


@pytest.fixture
async def pid(db):
    name = "test_project_1234"
    await db.execute(f"INSERT INTO projects (name, default_language_id, published) VALUE ('{name}', 1, 1)")
    await db.execute(
        f"INSERT INTO project_information (name, lang_id, project_id) "
        f"VALUE ('{name}', 1, (SELECT id FROM projects WHERE name = '{name}'))"
    )
    yield name
    await db.execute(f"DELETE FROM projects WHERE name = '{name}'")


@pytest.fixture
async def dpid(db):
    name = "test_project_12345678"
    yield name
    await db.execute(f"DELETE FROM projects WHERE name = '{name}'")


@pytest.fixture
async def user(pid, db):
    username = "test_user#1234"
    email = "testman@example.com"
    _id = await db.fetch_val(
        """
        INSERT INTO users (username, email) VALUE (:uname, :email) RETURNING id
        """,
        values=dict(uname=username, email=email)
    )
    await db.execute(
        """
        INSERT INTO project_admins (project_id, user_id) SELECT id, :uid FROM projects WHERE name = :p
        """,
        values=dict(p=pid, uid=_id)
    )
    await db.execute(
        """
        INSERT INTO superusers (user_id) SELECT :uid
        """,
        values=dict(uid=_id)
    )
    yield username
    await db.execute("DELETE FROM users WHERE id = :id", values=dict(id=_id))


def create_request(*required_scopes, token=b"1234", projects=None):
    """Create requests with different scopes for testing
    """
    r = Request(dict(type="http", user=User.null()))
    r.user.username = "test_user#1234"
    r.user.scopes = set(required_scopes)
    r.user.scopes.add(scopes.AUTHENTICATED)
    r.user.admin_projects = projects or list()
    r.user.token = token
    return r.user, "en"


@pytest.mark.anyio
async def test_delete_project(db, pid):
    repo = ProjectRepo(db)
    repo.configure(*create_request(scopes.SUPERUSER))
    await repo.delete(pid)
    assert await db.fetch_val(f"SELECT NOT EXISTS(SELECT 1 FROM projects WHERE name = '{pid}')")


@pytest.mark.anyio
async def test_change_default_lang(db, pid, user):
    repo = ProjectRepo(db)
    repo.configure(*create_request(scopes.ADMIN, projects=[pid]))
    assert await db.fetch_val(f"SELECT default_language_id FROM projects WHERE name = '{pid}'") == 1
    await repo.modify(pid, ModifiedProject(default_language="en"))
    assert await db.fetch_val(f"SELECT default_language_id FROM projects WHERE name = '{pid}'") == 2


@pytest.mark.anyio
async def test_change_start_end(db, pid, user):
    repo = ProjectRepo(db)
    repo.configure(*create_request(scopes.ADMIN, projects=[pid]))
    assert await db.fetch_val(f"SELECT (starts IS NULL AND ends IS NULL) FROM projects WHERE name = '{pid}'")
    await repo.modify(pid, ModifiedProject(
        starts=datetime.datetime.fromisoformat("2021-01-01"),
        ends=datetime.datetime.fromisoformat("2021-02-03")
    ))
    assert await db.fetch_val(f"SELECT (starts IS NOT NULL AND ends IS NOT NULL) FROM projects WHERE name = '{pid}'")


@pytest.mark.anyio
async def test_change_contact(db, pid, user):
    repo = ProjectRepo(db)
    repo.configure(*create_request(scopes.ADMIN, projects=[pid]))
    assert await db.fetch_val(
        f"SELECT 1 FROM project_contact pc JOIN projects p on pc.project_id = p.id WHERE p.name = '{pid}'"
    ) is None
    await repo.modify(pid, ModifiedProject(
        contact=ProjectContact(
            can_contact=True,
            has_research_permit=True,
            contact_email="a@example.com"
        )
    ))
    assert await db.fetch_val(
        f"SELECT 1 FROM project_contact pc JOIN projects p on pc.project_id = p.id WHERE p.name = '{pid}'"
    )


@pytest.mark.anyio
async def test_admin_removed_in_db_exists_in_session_errors(db, pid):
    repo = ProjectRepo(db)
    repo.configure(*create_request(scopes.ADMIN, projects=[pid]))
    with pytest.raises(HTTPException) as e:
        await repo.modify(pid, ModifiedProject(
            contact=ProjectContact(
                can_contact=True,
                has_research_permit=True,
                contact_email="a@example.com"
            )
        ))
    assert e.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.anyio
async def test_empty_model_returns_false(db, pid, user):
    repo = ProjectRepo(db)
    repo.configure(*create_request(scopes.ADMIN, projects=[pid]))
    return not await repo.modify(pid, ModifiedProject.construct())


@pytest.mark.anyio
async def test_create_raises(db, user):
    repo = ProjectRepo(db)
    repo.configure(*create_request(scopes.ADMIN))
    with pytest.raises(HTTPException) as e:
        await repo.create(NewProject(id="adadwdwddaw_Dwdadadawdawd", info=ProjectInfo(name="aaawdad", lang="fi")))
    assert e.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Not enough privileges" in e.value.detail


@pytest.mark.anyio
async def test_contact_none_deletes(db, pid, user):
    repo = ProjectRepo(db)
    repo.configure(*create_request(scopes.ADMIN, projects=[pid]))
    await db.execute(
        """
        INSERT INTO project_contact (project_id, contact_email) 
        SELECT id, 'a@example.com' FROM projects WHERE name = :pid
        """,
        values=dict(pid=pid)
    )
    assert await db.fetch_val(
        """
        SELECT COUNT(*) FROM project_contact JOIN projects p WHERE p.name = :pid
        """,
        values=dict(pid=pid)
    )
    assert await repo.modify(pid, ModifiedProject(
        contact=None
    ))
    assert await db.fetch_val(
        """
        SELECT NOT EXISTS(SELECT 1 FROM project_contact JOIN projects p WHERE p.name = :pid)
        """,
        values=dict(pid=pid)
    )


@pytest.mark.anyio
async def test_localization_none_returns_false(db, pid, user):
    repo = ProjectRepo(db)
    repo.configure(*create_request(scopes.ADMIN, projects=[pid]))
    assert not await repo.modify(pid, ModifiedProject(
        info=None
    ))


@pytest.mark.anyio
async def test_create_project_contact_none_ok(db, dpid, user):
    repo = ProjectRepo(db)
    repo.configure(*create_request(scopes.SUPERUSER))
    await repo.create(NewProject(
        id=dpid,
        contact=None,
        info=ProjectInfo(
            name="asdwadwadwdaw",
            lang="fi"
        )
    ))
    assert (await repo.one(dpid)).contact is None


@pytest.mark.anyio
async def test_create_project_contact_ok(db, dpid, user):
    repo = ProjectRepo(db)
    repo.configure(*create_request(scopes.SUPERUSER))
    await repo.create(NewProject(
        id=dpid,
        contact=ProjectContact(
            contact_email="a@eaxmple.com",
            can_contact=True,
            has_research_permit=False,
        ),
        info=ProjectInfo(
            name="asdwadwadwdaw",
            lang="fi"
        )
    ))
    assert await db.fetch_val(
        """
        SELECT EXISTS(SELECT 1 FROM project_contact JOIN projects p WHERE p.name = :pid)
        """,
        values=dict(pid=dpid)
    )


@pytest.mark.anyio
async def test_project_ended(db, pid):
    repo = ProjectRepo(db)
    repo.configure(*create_request())
    await db.execute(
        """
        UPDATE projects SET ends = ADDDATE(CURDATE(), -5) WHERE name = :pid
        """,
        values=dict(pid=pid)
    )
    with pytest.raises(HTTPException) as e:
        await repo.one(pid)
    assert e.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.anyio
async def test_project_not_yet_started(db, pid):
    repo = ProjectRepo(db)
    repo.configure(*create_request())
    await db.execute(
        """
        UPDATE projects SET starts = ADDDATE(CURDATE(), 5) WHERE name = :pid
        """,
        values=dict(pid=pid)
    )
    with pytest.raises(HTTPException) as e:
        await repo.one(pid)
    assert e.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.anyio
async def test_project_not_yet_started_admin_ok(db, pid, user):
    repo = ProjectRepo(db)
    repo.configure(*create_request(scopes.ADMIN))
    await db.execute(
        """
        UPDATE projects SET starts = ADDDATE(CURDATE(), 5) WHERE name = :pid
        """,
        values=dict(pid=pid)
    )
    assert await repo.one(pid) is not None


@pytest.mark.anyio
async def test_project_not_yet_started_admin_all_ok(db, pid, user):
    repo = ProjectRepo(db)
    repo.configure(*create_request(scopes.ADMIN))
    await db.execute(
        """
        UPDATE projects SET starts = ADDDATE(CURDATE(), 5) WHERE name = :pid
        """,
        values=dict(pid=pid)
    )
    assert len(await repo.all()) != 0


@pytest.mark.anyio
async def test_project_dates_ok(db, pid):
    repo = ProjectRepo(db)
    repo.configure(*create_request())
    await db.execute(
        """
        UPDATE projects SET starts = ADDDATE(CURDATE(), -5), ends = ADDDATE(CURDATE(), 5) WHERE name = :pid
        """,
        values=dict(pid=pid)
    )
    p = await repo.one(pid)
    assert p.id == pid
    assert p.starts is not None
    assert p.ends is not None


@pytest.mark.anyio
async def test_project_contact_ok(db, pid):
    repo = ProjectRepo(db)
    repo.configure(*create_request())
    p = await repo.one(pid)
    assert p.id == pid
    assert p.contact is None
    await db.execute(
        """
        INSERT INTO project_contact (project_id) SELECT id FROM projects WHERE name = :pid
        """,
        values=dict(pid=pid)
    )
    p = await repo.one(pid)
    assert p.id == pid
    assert p.contact is not None
