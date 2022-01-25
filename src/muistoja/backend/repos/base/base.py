import inspect
import re
from abc import ABC, abstractmethod
from typing import List, Any, NoReturn, Union

from fastapi import Request, HTTPException, status

from .files import Files
from .status import Status
from .utils import extract_language
from ....core.config import Config
from ....core.database import Database
from ....core.logging import log
from ....core.security import User


class BaseRepo(ABC):
    """
    Base for Repo classes.

    These classes provide data to endpoints.
    Throwing HTTPExceptions is a good way to propagate exceptions.
    """

    def __init_subclass__(cls, **kwargs):
        """
        Checks Repo requirements and mistakes
        """

        resource = cls.__name__.removesuffix("Repo").lower()
        assert re.fullmatch('^[A-Z][a-z]+(?<!s)Repo$', cls.__name__)

        mro = inspect.getmro(cls)
        if not mro[1] == BaseRepo:
            log.warning(f'{cls.__name__} not inheriting base repo directly')
        funcs = mro[0].__dict__
        for name in ['_check_exists', '_check_not_exists']:
            assert name not in funcs
        for name in [f'construct_{resource}', '_exists']:
            if name not in funcs:
                log.warning(f'No {name} declared in repo {cls.__name__}')

    def __init__(self, db: Database, **kwargs):
        self.db = db
        for k, v in kwargs.items():
            setattr(self, k, v)
        self._user: Union[User] = User()
        self.lang = "fi"
        self.auto_publish = Config.security.auto_publish

    def configure(self, r: Request):
        """
        Adds configuration data from the Request to this repo

        Adds:

        - User
        - Language
        """
        self._user = r.user
        try:
            self.lang = extract_language(r)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail='Can not localize')
        return self

    def _configure(self, repo: 'BaseRepo'):
        self._user = repo._user
        self.lang = repo.lang
        return self

    @abstractmethod
    async def all(self, *args) -> List:
        """
        Return all resources matching arguments.
        """
        pass

    @abstractmethod
    async def one(self, *args) -> Any:
        """
        Return a single resource. Return a model class.
        """
        pass

    @abstractmethod
    async def create(self, model) -> Any:
        """
        Create a resource. Return identifier on success.
        """
        pass

    @abstractmethod
    async def modify(self, *args) -> bool:
        """
        Modify a resource. Return whether the resource changed.
        """
        pass

    @abstractmethod
    async def delete(self, *args) -> NoReturn:
        """
        Delete the resource
        """
        pass

    @abstractmethod
    async def toggle_publish(self, *args) -> NoReturn:
        """
        Set publish
        """
        pass

    @abstractmethod
    async def _exists(self, arg) -> Status:
        """
        Check whether a single Repo resource exists.

        Should check if prerequisites exist too.
        """
        pass

    async def _set_published(self, published: bool, **values) -> NoReturn:
        """
        Changes published status for a Repo

        Usage:

        @set_published(False)
        def delete(self, *args, **kwargs)
            return "WHERE PART", DICT[VALUES]

        :param published: 1 if published else 0
        :return:          Decorated function
        """
        await self.db.execute(
            f'UPDATE {type(self).__name__.removesuffix("Repo").lower()}s r'
            f' LEFT JOIN users u ON u.username = :user'
            f' SET r.published = {1 if published else 0}, r.modifier_id = u.id'
            f' WHERE {" AND ".join(f"{k} = :{k}" for k in values.keys())}',
            values={**values, 'user': self.identity}
        )

    @property
    def identity(self):
        return self._user.identity if self._user.is_authenticated else None

    @property
    def has_identity(self):
        return self.identity is not None

    @property
    def is_admin(self):
        return self._user.is_authenticated and (
            self._user.is_admin_in(self.project)
            if hasattr(self, 'project')
            else self.is_superuser
        )

    @property
    def is_superuser(self):
        return self._user.is_superuser

    @property
    def files(self):
        return Files(self.db, self._user)

    def _saoh(self, m, s: Status, idx_admin: int, idx_own: int):
        """
        Helper for admin, self checks
        """
        if self.has_identity and s != Status.DOES_NOT_EXIST:
            admin = m[idx_admin] == 0
            own = m[idx_own] == self.identity

            if admin and own:
                return Status.OWN_AND_ADMIN
            elif admin:
                return Status.ADMIN
            elif own:
                return Status.OWN


__all__ = ['BaseRepo']
