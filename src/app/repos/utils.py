import functools
from typing import Set, Callable

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


def _name(o):
    return type(o).__name__.removesuffix('Repo')


def _check_kwargs(f) -> Optional[str]:
    from inspect import signature

    kwrd = None
    for k, v in signature(f).parameters.items():
        if v.kind == v.KEYWORD_ONLY and v.annotation == Status:
            kwrd = v.name

    return kwrd


async def _exists(*args) -> Status:
    if len(args) >= 2:
        from pydantic import BaseModel
        self, arg = args[0:2]
        if isinstance(arg, BaseModel):
            if hasattr(arg, 'id'):
                arg = arg.id
            else:
                arg = None
        exists = await self._exists(arg)
    else:
        self = args[0]
        exists = await self._exists(None)
    return exists


def _mapper_common(self, s):
    if s == Status.DOES_NOT_EXIST:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'{_name(self)} not found')
    else:
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not enough privileges')


def check(
        allowed_types: Set[Status],
        error_mapper: Optional[Callable[[BaseRepo, Status], HTTPException]],
        *,
        invert: bool = False
):
    """
    General check function
    """

    def _decorator(f):
        kwrd = _check_kwargs(f)

        @functools.wraps(f)
        async def decorator(*args, **kwargs):
            s = await _exists(*args)
            if s not in allowed_types if invert else s in allowed_types:
                if kwrd is None:
                    return await f(*args, **kwargs)
                else:
                    return await f(*args, **{**kwargs, kwrd: s})
            else:
                if error_mapper is not None:
                    raise error_mapper(args[0], s)

        return decorator

    return _decorator


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
    return check(
        {Status.DOES_NOT_EXIST},
        lambda self, s: HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'{_name(self)} not found'),
        invert=True
    )(f)


def check_not_exists(f):
    """
    Opposite of 'check_exists'
    """
    return check(
        {Status.DOES_NOT_EXIST},
        lambda self, s: HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f'{_name(self)} exists')
    )(f)


def check_parents(f):
    """
    Checks just parents
    """
    return check(
        set(),
        None,
        invert=True
    )(f)


def check_admin(f):
    """
    Check user is admin
    """

    return check(
        {Status.ADMIN},
        _mapper_common
    )(f)


def check_own(f):
    """
    Check user is admin
    """

    return check(
        {Status.OWN},
        _mapper_common
    )(f)


def check_published_or_admin(f):
    """
    Check exists and published

    Admins will bypass this
    """
    return check(
        {Status.PUBLISHED, Status.OWN, Status.ADMIN},
        _mapper_common
    )(f)


def check_own_or_admin(f):
    """
    Check own or admin

    Admins will bypass this
    """
    return check(
        {Status.OWN, Status.ADMIN},
        _mapper_common
    )(f)


def check_super(f):
    """
    Only Super will bypass
    """
    return check(
        set(),
        _mapper_common
    )(f)


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
