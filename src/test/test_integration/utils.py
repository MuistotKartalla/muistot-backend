import random

from databases import Database
from passlib.pwd import genword

from app.config import Config
from app.models import *
from app.repos import *


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
    def url(self):
        url = ''
        if hasattr(self, 'project'):
            url += f'/projects/{self.project}'
        if hasattr(self, 'site'):
            url += f'/sites/{self.site}'
        if hasattr(self, 'memory'):
            url += f'/memories/{self.memory}'
        return url

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return self.url


async def create_memory(pid: PID, sid: SID, db: Database, config, **additional_properties) -> MID:
    out = await MemoryRepo(db, pid, sid).configure(config).create(NewMemory(
        title=genword(length=100),
        story=genword(length=1500),
        **additional_properties
    ))
    assert isinstance(out, MID), f"Was {type(out)}: {repr(out)}"
    await db.execute(f"UPDATE memories SET published = 1 WHERE id = :id", values=dict(id=out))
    return out


async def create_comment(pid: PID, sid: SID, mid: MID, db, config) -> CID:
    out = await CommentRepo(db, pid, sid, mid).configure(config).create(NewComment(
        comment=genword(length=500)
    ))
    assert isinstance(out, CID), f"Was {type(out)}: {repr(out)}"
    await db.execute(f"UPDATE comments SET published = 1 WHERE id = :id", values=dict(id=out))
    return out


def create_site_info(lang: str) -> SiteInfo:
    return SiteInfo(
        name=genword(length=10),
        abstract=genword(length=100),
        lang=lang,
        description=genword(length=1500)
    )


async def create_site(pid: PID, db, config, **additional_properties) -> SID:
    out = await SiteRepo(db, pid).configure(config).create(NewSite(
        id=genword(length=10),
        info=create_site_info(Config.default_language),
        location=Point(
            lat=random.randint(0, 89) + random.random(),
            lon=random.randint(1, 71) + random.random()
        ),
        **additional_properties
    ))
    assert isinstance(out, SID), f"Was {type(out)}: {repr(out)}"
    await db.execute(f"UPDATE sites SET published = 1 WHERE name = :id", values=dict(id=out))
    return out


def create_project_info(lang: str) -> ProjectInfo:
    return ProjectInfo(
        name=genword(length=10),
        abstract=genword(length=100),
        lang=lang,
        description=genword(length=1500)
    )


async def create_project(db, config, **additional_properties) -> PID:
    out = await ProjectRepo(db).configure(config).create(NewProject(
        id=genword(length=10),
        info=create_project_info(Config.default_language),
        **additional_properties
    ))
    assert isinstance(out, PID), f"Was {type(out)}: {repr(out)}"
    await db.execute(f"UPDATE projects SET published = 1 WHERE name = :id", values=dict(id=out))
    return out
