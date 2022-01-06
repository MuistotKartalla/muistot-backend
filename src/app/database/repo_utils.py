import functools
import inspect
from abc import ABC, abstractmethod
from typing import List, Any, Optional, NoReturn, Union

from fastapi import Request, HTTPException, status

from .connections import Database
from ..models import *
from ..utils import extract_language_or_default


def not_implemented(f):
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
    @functools.wraps(f)
    async def decorator(*args, **kwargs):
        await args[0]._check_exists(args[1])
        return await f(*args, **kwargs)

    return decorator


def check_not_exists(f):
    @functools.wraps(f)
    async def decorator(*args, **kwargs):
        await args[0]._check_not_exists(args[1])
        return await f(*args, **kwargs)

    return decorator


class BaseRepo(ABC):

    def __init_subclass__(cls, **kwargs):
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
        self.user = r.user
        self.lang = extract_language_or_default(r)

    async def check_admin_privilege(self, project: Optional[str]) -> NoReturn:
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
        pass

    @abstractmethod
    async def one(self, *args) -> Any:
        pass

    @abstractmethod
    async def create(self, model) -> Any:
        pass

    @abstractmethod
    async def modify(self, *args) -> bool:
        pass

    @abstractmethod
    async def delete(self, *args):
        pass

    @abstractmethod
    async def publish(self, *args):
        pass

    @abstractmethod
    async def _exists(self, arg) -> bool:
        pass

    async def _check_exists(self, arg):
        if not await self._exists(arg):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'{type(self).__name__.removesuffix("Repo")} not found'
            )

    async def _check_not_exists(self, arg):
        if await self._exists(arg):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f'{type(self).__name__.removesuffix("Repo")} already exists'
            )


class Files:

    def __init__(self, db: Database):
        self.db = db

    async def handle(self, file_data: str):
        if file_data is not None:
            from ..utils import check_file
            from ..config import Config
            data = check_file(file_data)
            if data is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Bad image')
            m = await self.db.fetch_one("INSERT INTO images VALUE () RETURNING id, file_name")
            image_id = m[0]
            file_name = m[1]
            with open(f'{Config.files.location}{file_name}', 'wb') as f:
                f.write(data)
            return image_id


def check_id(_id: str):
    from ..utils import url_safe
    if not url_safe(_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Bad identifier')


def check_language(lang: str):
    from ..utils import get_languages
    if lang not in get_languages():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Bad language')
