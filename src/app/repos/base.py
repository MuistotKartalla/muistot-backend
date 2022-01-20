import inspect
from abc import ABC, abstractmethod
from enum import IntEnum
from typing import List, Any, Optional, NoReturn, Union

from fastapi import Request, HTTPException, status

from ..config import Config
from ..database import Database
# noinspection PyUnresolvedReferences
from ..models import *
from ..utils import extract_language


class Status(IntEnum):
    DOES_NOT_EXIST = -1
    NOT_PUBLISHED = 0
    PUBLISHED = 1
    OWN = 3
    ADMIN = 9

    @staticmethod
    def resolve(value: Optional[int]) -> 'Status':
        if value is None:
            return Status.DOES_NOT_EXIST
        elif value == 1:
            return Status.PUBLISHED
        else:
            return Status.NOT_PUBLISHED


class Files:
    """
    Interfacing with files in base64 strings
    """

    def __init__(self, db: Database, user: Any):
        self.db = db
        self.user = user

    async def handle(self, file_data: str) -> int:
        """
        Handle incoming image file data.

        Checks filetype and saves the file.
        Name is generated from Database defaults.

        :param file_data:   data in base64
        :return:            image_id if one was generated
        """
        if file_data is not None and (Config.files.allow_anonymous or self.user.is_authenticated):
            from ..utils import check_file
            data, file_type = check_file(file_data)
            if data is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Bad image')
            if self.user.is_authenticated:
                m = await self.db.fetch_one(
                    """
                    INSERT INTO images (uploader_id) 
                    SELECT
                        u.id 
                    FROM users u
                        WHERE u.username = :user
                    RETURNING id, file_name
                    """,
                    values=dict(ft=file_type, user=self.user.identity)
                )
            else:
                m = await self.db.fetch_one("INSERT INTO images VALUE () RETURNING id, file_name")
            image_id = m[0]
            file_name = m[1]
            with open(f'{Config.files.location}{file_name}', 'wb') as f:
                f.write(data)
            return image_id


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
        from ..logging import log
        import re
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
        from ..security.auth import User
        self.db = db
        for k, v in kwargs.items():
            setattr(self, k, v)
        self._user: Union[User] = User()
        self.lang = "fi"
        self.auto_publish = Config.auto_publish

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
