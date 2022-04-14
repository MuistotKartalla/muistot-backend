import random
from typing import TypeVar, Type
from typing import cast
from urllib.parse import quote

from fastapi import Request
from headers import AUTHORIZATION
from muistot.backend.models import *
from muistot.backend.repos import *
from muistot.config import Config
from muistot.security.auth import User
from muistot.security.scopes import ADMIN, AUTHENTICATED, SUPERUSER

from urls import *

T = TypeVar('T')


class Setup:
    project: PID
    site: SID
    memory: MID

    def __init__(self, *args):
        length = len(args)
        if length == 3:
            self.project, self.site, self.memory = args
        elif length == 2:
            self.project, self.site = args
        else:
            self.project = args[0]

    @property
    def _url(self):
        url = ROOT
        values = []
        if hasattr(self, "project"):
            values.append(self.project)
            url = PROJECT
        if hasattr(self, "site"):
            values.append(self.site)
            url = SITE
        if hasattr(self, "memory"):
            values.append(self.memory)
            url = MEMORY
        return url.format(*(quote(str(o)) for o in values))

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return self._url

    def __iter__(self):
        return iter(quote(str(getattr(self, o))) for o in ["project", "site", "memory"] if hasattr(self, o))


def genword(length=10):
    from secrets import choice
    from string import ascii_letters, digits
    pool = ascii_letters + digits + "-_"
    return ''.join(choice(pool) for _ in range(0, length))


async def create_memory(pid: PID, sid: SID, db, config, **additional_properties) -> MID:
    out = await MemoryRepo(db, pid, sid).configure(config).create(
        NewMemory(
            title=genword(length=100),
            story=genword(length=1500),
            **additional_properties,
        )
    )
    assert out is not None
    await db.execute("UPDATE memories SET published = 1 WHERE id = :id", values=dict(id=out))
    return out


async def create_comment(pid: PID, sid: SID, mid: MID, db, config) -> CID:
    out = await CommentRepo(db, pid, sid, mid).configure(config).create(NewComment(comment=genword(length=500)))
    assert out is not None
    await db.execute("UPDATE comments SET published = 1 WHERE id = :id", values=dict(id=out))
    return out


def create_site_info(lang: str) -> SiteInfo:
    return SiteInfo(
        name=genword(length=10),
        abstract=genword(length=100),
        lang=lang,
        description=genword(length=1500),
    )


async def create_site(pid: PID, db, config, **additional_properties) -> SID:
    out = (
        await SiteRepo(db, pid)
            .configure(config)
            .create(
            NewSite(
                id=genword(length=10),
                info=create_site_info(Config.localization.default),
                location=Point(
                    lat=random.randint(0, 89) + random.random(),
                    lon=random.randint(1, 71) + random.random(),
                ),
                **additional_properties,
            )
        )
    )
    assert out is not None
    await db.execute("UPDATE sites SET published = 1 WHERE name = :id", values=dict(id=out))
    return out


def create_project_info(lang: str) -> ProjectInfo:
    return ProjectInfo(
        name=genword(length=10),
        abstract=genword(length=100),
        lang=lang,
        description=genword(length=1500),
    )


async def create_project(db, config, **additional_properties) -> PID:
    out = await ProjectRepo(db).configure(config).create(
        NewProject(
            id=genword(length=10),
            info=create_project_info(Config.localization.default),
            **additional_properties,
        )
    )
    assert out is not None
    assert (await db.fetch_val("SELECT COUNT(*) FROM projects WHERE name = :name", values=dict(name=out))) == 1, out
    await db.execute("UPDATE projects SET published = 1 WHERE name = :id", values=dict(id=out))
    return out


def mock_request(username):
    uid = username

    u = User()
    u.username = uid
    u.scopes.update({SUPERUSER, AUTHENTICATED, ADMIN})

    class MockRequest:
        method = "GET"
        headers = dict()
        user = u

    return cast(Request, MockRequest())


def authenticate(client, username, password):
    r = client.post(
        LOGIN,
        json={"username": username, "password": password},
        allow_redirects=True,
    )
    check_code(200, r)
    auth = r.headers[AUTHORIZATION]
    return {AUTHORIZATION: auth}


def to(model: Type[T], r) -> T:
    try:
        return model(**r.json())
    except Exception as e:
        assert False, f"Failed model creation\n - ex: {e}\n - status: {r.status_code}\n - content: {r.content}"


def check_code(code: int, r):
    assert r.status_code == code, f"wrong return code:\n - expected: {code}\n - returned: {r.status_code}\n{r.content}"


def extract_id(r, _type=int):
    """Extract entity id from response
    """
    from headers import LOCATION
    return _type(r.headers[LOCATION].removesuffix("/").split("/")[-1])
