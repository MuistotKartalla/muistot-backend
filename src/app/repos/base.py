import inspect
from abc import ABC, abstractmethod
from typing import List, Any, Optional, NoReturn, Union

from fastapi import Request, HTTPException, status

from ..database import Database
from ..models import *
from ..utils import extract_language
from ..config import Config


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
        from starlette.authentication import UnauthenticatedUser
        from ..security.auth import CustomUser
        self.db = db
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.user: Union[UnauthenticatedUser, CustomUser] = UnauthenticatedUser()
        self.lang = "fi"
        self.auto_publish = Config.auto_publish

    def configure(self, r: Request):
        """
        Adds configuration data from the Request to this repo

        Adds:

        - User
        - Language
        """
        self.user = r.user
        try:
            self.lang = extract_language(r)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail='Can not localize')

    async def check_admin_privilege(self, project: Optional[PID]) -> NoReturn:
        """
        Check if the current user is admin for the selected project

        If project is None only SuperUsers are accepted.
        """
        from ..security.auth import SuperUser
        if isinstance(self.user, SuperUser):
            return
        elif project is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unauthorized\nNot enough privileges')
        elif self.user.is_authenticated and self.user.is_admin_in(project):
            is_admin = await self.db.fetch_val(
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
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unauthorized\nNot an admin')

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
    async def _exists(self, arg) -> bool:
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
            f'UPDATE {type(self).__name__.removesuffix("Repo").lower()}s'
            f' SET published = {1 if published else 0}'
            f' WHERE {" AND ".join(f"{k} = :{k}" for k in values.keys())}',
            values=values
        )


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
