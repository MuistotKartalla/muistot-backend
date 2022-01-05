from abc import ABC, abstractmethod
from typing import List, Any, Optional, NoReturn, Union

from fastapi import Request, HTTPException, status

from .connections import Database
from ..models import *
from ..utils import extract_language_or_default


def needs_admin(f):
    import functools
    import inspect

    param_index = None
    for idx, name in enumerate(inspect.getfullargspec(f).args):
        if name == 'project':
            param_index = idx
            break

    if param_index is None:
        @functools.wraps(f)
        async def decorator(*args, **kwargs):
            self: 'BaseRepo' = args[0]
            project: PID = getattr(self, 'project')
            await self.check_admin_privilege(project)
            return await f(*args, **kwargs)
    else:
        @functools.wraps(f)
        async def decorator(*args, **kwargs):
            self: 'BaseRepo' = args[0]
            project: PID = args[param_index]
            await self.check_admin_privilege(project)
            return await f(*args, **kwargs)

    return decorator


class BaseRepo(ABC):

    def __init__(self, db: Database, **kwargs):
        from starlette.authentication import UnauthenticatedUser
        from ..security.auth import CustomUser
        from ..config import Config
        self.db = db
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.user: Union[UnauthenticatedUser, CustomUser] = UnauthenticatedUser()
        self.lang = "fi"
        self.publish = Config.auto_publish

    def configure(self, r: Request):
        self.user = r.user
        self.lang = extract_language_or_default(r)

    async def check_admin_privilege(self, project: str) -> NoReturn:
        if self.user.is_authenticated and self.user.is_admin_in(project):
            is_admin = self.db.execute(
                """
                SELECT EXISTS(
                    SELECT 1
                    FROM users u
                        JOIN project_admins pa ON pa.user_id = u.id
                        JOIN projects p ON pa.project_id = p.id
                    WHERE p.name = :project AND u.username = :user
                )
                """,
                values=dict(project=project, user=self.user.identity)
            )
            if not is_admin:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unauthorized')

    @abstractmethod
    async def all(self, *args) -> List:
        pass

    @abstractmethod
    async def one(self, *args) -> Any:
        pass

    @abstractmethod
    async def create(self, model) -> Any:
        pass

    @abstractmethod
    async def delete(self, *args) -> bool:
        pass

    @abstractmethod
    async def modify(self, *args) -> bool:
        pass

    @abstractmethod
    async def by_user(self, user: str) -> List:
        pass


class ProjectRepo(BaseRepo):

    async def make_project(self, m):
        if m is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        pi = ProjectInfo.construct(ProjectInfo.__fields_set__, **m)
        if not m[8] is None:
            pc = ProjectContact.construct(ProjectContact.__fields_set__, **m)
        else:
            pc = None
        return Project.construct(
            Project.__fields_set__,
            **m,
            info=pi,
            contact=pc,
            admins=[admin[0] async for admin in self.db.iterate(
                """
                SELECT
                    u.username
                FROM project_admins pa
                    JOIN users u ON pa.user_id = u.id
                WHERE project_id = :pid
                """,
                values=dict(pid=m[0])
            )]
        )

    async def all(self) -> List[Project]:
        return [await self.make_project(m) async for m in self.db.iterate(
            """
            SELECT
                p.id AS project_id,
                p.name AS id,
                
                l.lang,
                IFNULL(pi.name, p.name) AS name,
                pi.abstract,
                pi.description,
                
                p.starts,
                p.ends,
                
                pc.has_research_permit,
                IF(pc.can_contact, pc.contact_email, NULL)
            FROM projects p
                JOIN images i ON p.image_id = i.id
                LEFT JOIN project_contact pc ON p.id = pc.project_id
                LEFT JOIN project_information pi ON p.id = pi.project_id
                JOIN languages l ON pi.lang_id = l.id
                    AND l.lang = :lang
            WHERE IFNULL(p.starts > CURDATE(), TRUE) AND p.published
            """,
            values=dict(lang=self.lang)
        )]

    async def one(self, project: PID) -> Project:
        return await self.make_project(await self.db.fetch_one(
            """
            SELECT
                p.id AS project_id,
                p.name AS id,
                
                l.lang,
                IFNULL(pi.name, p.name) AS name,
                pi.abstract,
                pi.description,
                
                p.starts,
                p.ends,
                
                pc.has_research_permit,
                IF(pc.can_contact, pc.contact_email, NULL)
            FROM projects p
                JOIN images i ON p.image_id = i.id
                LEFT JOIN project_contact pc ON p.id = pc.project_id
                LEFT JOIN project_information pi ON p.id = pi.project_id
                JOIN languages l ON pi.lang_id = l.id
                    AND l.lang = :lang
            WHERE IFNULL(p.starts > CURDATE(), TRUE) AND p.published
                AND p.name = :project
            """,
            values=dict(lang=self.lang, project=project)
        ))

    @needs_admin  # This will imply SuperUser
    async def create(self, model: Project) -> PID:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)

    @needs_admin
    async def modify(self, project: PID, model: ModifiedProject) -> bool:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)

    @needs_admin
    async def delete(self, project: PID):
        await self.db.execute(
            "UPDATE projects SET published = 0 WHERE name = :project",
            values=dict(project=project)
        )

    async def by_user(self, user: str) -> List:
        """Not used"""
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)

    @needs_admin
    async def publish(self, project: PID) -> PID:
        await self.db.execute(
            "UPDATE projects SET published = 1 WHERE name = :project",
            values=dict(project=project)
        )
        return project


class SiteRepo(BaseRepo):

    def __init__(self, db: Database, project: PID):
        super().__init__(db, project=project)

    async def all(
            self,
            n: Optional[int],
            lat: Optional[float],
            lon: Optional[float]
    ) -> List[Site]:
        pass

    async def one(self, site: SID) -> Site:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)

    async def create(self, model: NewSite) -> SID:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)

    @needs_admin
    async def modify(self, site: SID, model: ModifiedSite) -> bool:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)

    @needs_admin
    async def delete(self, site: SID) -> bool:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)

    async def by_user(self, user: str) -> List[Site]:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)

    @needs_admin
    async def publish(self, site: SID) -> SID:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)


class MemoryRepo(BaseRepo):

    def __init__(self, db: Database, project: PID, site: SID):
        super().__init__(db, project=project, site=site)

    async def all(self) -> List[Memory]:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)

    async def one(self, memory: MID) -> Memory:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)

    async def create(self, model: NewMemory) -> MID:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)

    async def modify(self, memory: MID, model: ModifiedMemory) -> bool:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)

    async def delete(self, memory: MID) -> bool:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)

    async def by_user(self, user: str) -> List[Memory]:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)


class CommentRepo(BaseRepo):

    def __init__(self, db: Database, project: PID, site: SID, memory: MID):
        super().__init__(db, project=project, site=site, memory=memory)

    async def all(self) -> List[Comment]:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)

    async def one(self, comment: CID) -> Comment:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)

    async def create(self, model: NewComment) -> CID:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)

    async def modify(self, comment: CID, model: ModifiedComment) -> bool:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)

    async def delete(self, *args) -> bool:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)

    async def by_user(self, user: str) -> List[Comment]:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)


__all__ = [
    'ProjectRepo',
    'SiteRepo',
    'MemoryRepo',
    'CommentRepo'
]
