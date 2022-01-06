import functools
import inspect
from abc import ABC, abstractmethod
from typing import List, Any, Optional, NoReturn, Union

from fastapi import Request, HTTPException, status

from .connections import Database
from ..models import *
from ..utils import extract_language_or_default


def not_implemented(f):
    """
    Marks function as not used and generates a warning on startup

    Should only be used on Repo instance methods
    """
    from ..logging import log
    log.warning(f'Function not implemented {repr(f)}')

    @functools.wraps(f)
    async def decorator(*_, **__):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail='Not Implemented'
        )

    return decorator


def set_published(published: bool):
    """
    Changes published status for a Repo

    Usage:

    @set_published(False)
    def delete(self, *args, **kwargs)
        return "WHERE PART", DICT[VALUES]

    :param published: 1 if published else 0
    :return:          Decorated function
    """

    def factory(f):
        @functools.wraps(f)
        async def decorator(*args, **kwargs):
            res = await f(*args, **kwargs)
            self: 'BaseRepo' = args[0]
            await self.db.execute(
                f'UPDATE {type(self).__name__.removesuffix("Repo").lower()}s'
                f' SET published = {1 if published else 0}'
                f' WHERE {res[0]}',
                values=res[1]
            )

        return decorator

    return factory


def needs_admin(f):
    """
    Requires admin rights to a function
    Only works on Repo instance methods.


    Requires one:

    - Repo has field 'project' type 'PID'
    - Method has parameter named 'project' type 'PID'
    - Method requires SuperUser

    Usage:

    @needs_admin
    def do_something(*args, *kwargs):
        pass

    """
    param_index = None
    for idx, name in enumerate(inspect.signature(f).parameters.keys()):
        if name == 'project':
            param_index = idx
            break

    if param_index is None:
        @functools.wraps(f)
        async def decorator(*args, **kwargs):
            self: 'BaseRepo' = args[0]
            project: PID = getattr(self, 'project', None)
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


def check_lang(f):
    """
    Throw a 406 if the function argument is None

    This is used on some construct methods in Repos
    """

    @functools.wraps(f)
    async def decorator(*args):
        if args[1] is None:
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail=type(args[0]).__name__.removesuffix('Repo')
                       + ' not localized in '
                       + getattr(args[0], 'lang')
            )
        else:
            return await f(*args)

    return decorator


def check_exists(f):
    """
    Checks that the resource exists

    Works only on Repo instance methods where the first argument is an identifier for a
    resource the Repo represents

    Usage:

    @check_exists
    def one(project: PID):
        pass

    Will take the 'project' argument and use that for checking _exist method
    """

    @functools.wraps(f)
    async def decorator(*args, **kwargs):
        await args[0]._check_exists(args[1])
        return await f(*args, **kwargs)

    return decorator


def check_not_exists(f):
    """
    Opposite of 'check_exists'
    """

    @functools.wraps(f)
    async def decorator(*args, **kwargs):
        await args[0]._check_not_exists(args[1])
        return await f(*args, **kwargs)

    return decorator


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
        from ..config import Config
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
        self.lang = extract_language_or_default(r)

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
    async def delete(self, *args):
        """
        Delete or un-publish the resource
        """
        pass

    @abstractmethod
    async def publish(self, *args):
        """
        Set publish to True
        """
        pass

    @abstractmethod
    async def _exists(self, arg) -> bool:
        """
        Check whether a single Repo resource exists.

        Should check if prerequisites exist too.
        """
        pass

    async def _check_exists(self, arg):
        from pydantic import BaseModel
        if isinstance(arg, BaseModel):
            arg = arg.id
        if not await self._exists(arg):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'{type(self).__name__.removesuffix("Repo")} not found'
            )

    async def _check_not_exists(self, arg):
        from pydantic import BaseModel
        if isinstance(arg, BaseModel):
            arg = arg.id
        if await self._exists(arg):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f'{type(self).__name__.removesuffix("Repo")} already exists'
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
        from ..config import Config
        if file_data is not None and (Config.files.allow_anonymous or self.user.is_authenticated):
            from ..utils import check_file
            from ..config import Config
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


def check_id(_id: str):
    """
    Check that an id is safe for URLs.
    """
    from ..utils import url_safe
    if not url_safe(_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Bad identifier')


def check_language(lang: str):
    """
    Check that language is available in config.
    """
    from ..utils import get_languages
    if lang not in get_languages():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Bad language')
