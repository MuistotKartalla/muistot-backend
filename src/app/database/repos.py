from abc import ABC, abstractmethod
from typing import List, Any, Optional, NoReturn

from .connections import Database
from ..models import *


class BaseRepo(ABC):

    def __init__(self, db: Database, **kwargs):
        self.db = db
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.user = None

    def set_user(self, u: Any):
        self.user = u

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

    async def all(self) -> List[Project]:
        pass

    async def one(self, project: PID) -> Project:
        pass

    async def create(self, model: Project) -> PID:
        pass

    async def modify(self, project: PID, model: ModifiedProject) -> bool:
        pass

    async def delete(self, project: PID) -> bool:
        pass

    async def by_user(self, user: str) -> List:
        raise NotImplementedError()


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
        pass

    async def create(self, model: NewSite) -> SID:
        pass

    async def modify(self, site: SID, model: ModifiedSite) -> bool:
        pass

    async def delete(self, site: SID) -> bool:
        pass

    async def by_user(self, user: str) -> List[Site]:
        pass

    async def publish(self, site: SID) -> NoReturn:
        pass


class MemoryRepo(BaseRepo):

    def __init__(self, db: Database, project: PID, site: SID):
        super().__init__(db, project=project, site=site)

    async def all(self) -> List[Memory]:
        pass

    async def one(self, memory: MID) -> Memory:
        pass

    async def create(self, model: NewMemory) -> MID:
        pass

    async def modify(self, memory: MID, model: ModifiedMemory) -> bool:
        pass

    async def delete(self, memory: MID) -> bool:
        pass

    async def by_user(self, user: str) -> List[Memory]:
        pass


class CommentRepo(BaseRepo):

    def __init__(self, db: Database, project: PID, site: SID, memory: MID):
        super().__init__(db, project=project, site=site, memory=memory)

    async def all(self) -> List[Comment]:
        pass

    async def one(self, comment: CID) -> Comment:
        pass

    async def create(self, model: NewComment) -> CID:
        pass

    async def modify(self, comment: CID, model: ModifiedComment) -> bool:
        pass

    async def delete(self, *args) -> bool:
        pass

    async def by_user(self, user: str) -> List[Comment]:
        pass


__all__ = [
    'ProjectRepo',
    'SiteRepo',
    'MemoryRepo',
    'CommentRepo'
]
