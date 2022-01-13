import functools

from .base import *


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
            self: BaseRepo = args[0]
            project: PID = getattr(self, 'project', None)
            await self.check_admin_privilege(project)
            return await f(*args, **kwargs)
    else:
        @functools.wraps(f)
        async def decorator(*args, **kwargs):
            self: BaseRepo = args[0]
            project: PID = args[param_index]
            await self.check_admin_privilege(project)
            return await f(*args, **kwargs)

    return decorator


def _name(o):
    return type(o).__name__.removesuffix('Repo')


async def _exists(*args) -> bool:
    if len(args) > 1:
        from pydantic import BaseModel
        self, arg = args[0:2]
        if isinstance(arg, BaseModel):
            arg = arg.id
        exists = await self._exists(arg)
    else:
        self = args[0]
        exists = await self._exists(None)
    return exists


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
                detail=(
                        _name(args[0])
                        + ' missing localization in '
                        + getattr(args[0], 'lang')
                        + ' and default'
                )
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
        if await _exists(*args):
            return await f(*args, **kwargs)
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'{_name(args[0])} not found')

    return decorator


def check_not_exists(f):
    """
    Opposite of 'check_exists'
    """

    @functools.wraps(f)
    async def decorator(*args, **kwargs):
        if not await _exists(*args):
            return await f(*args, **kwargs)
        else:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f'{_name(args[0])} exists')

    return decorator


def check_parents(f):
    """
    Checks just parents
    """

    @functools.wraps(f)
    async def decorator(*args, **kwargs):
        await _exists(*args)
        return await f(*args, **kwargs)

    return decorator


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
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail='Bad language')
