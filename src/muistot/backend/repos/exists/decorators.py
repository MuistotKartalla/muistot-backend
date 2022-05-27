import functools
from typing import Callable, Optional, Any, Type

from fastapi import HTTPException, status

from .base import Status, Exists
from ..base import BaseRepo


def _name(repo: BaseRepo):
    """Actual type name from repo
    """
    return type(repo).__name__.removesuffix("Repo")


def _check_status_kwarg(f) -> Optional[str]:
    """Check if the status should be given to the function
    """
    from inspect import signature
    kwrd = None
    for k, v in signature(f).parameters.items():
        if (v.kind == v.POSITIONAL_OR_KEYWORD or v.kind == v.KEYWORD_ONLY) and v.annotation == Status:
            kwrd = v.name
    return kwrd


def _guess_arg(arg: Any):
    """Guess the id needed for exist check
    """
    from pydantic import BaseModel
    if isinstance(arg, BaseModel):
        if hasattr(arg, "id"):
            arg = arg.id
        else:
            arg = None
    return arg


def _import_service(repo: BaseRepo) -> Type[Exists]:
    """Imports an Exists checker
    """
    import importlib
    _type = _name(repo)
    return getattr(importlib.import_module(
        f".{_type.lower()}",
        __name__.removesuffix(".decorators")
    ), f"{_type}Exists")


async def _actual_exists(repo: BaseRepo, arg: Any) -> Status:
    """Handles exists checks for all repos

    Imports the required module and gets the exists checker.
    """
    kwargs = repo.identifiers
    kwargs[_name(repo).lower()] = arg
    service = _import_service(repo)(user=repo.user, db=repo.db, **kwargs)
    out = await service.exists()

    repo.auto_publish = Status.AUTO_PUBLISH in out
    if repo.lang is None:
        repo.lang = service.default_language

    return out | Status.SUPER if repo.superuser else out


async def _exists(*args) -> Status:
    """Internal exists wrapper for check
    """
    res: Status
    self = args[0]
    if len(args) >= 2:
        arg = _guess_arg(args[1])
        res = await _actual_exists(self, arg)
    else:
        res = await _actual_exists(self, None)
    return res


def _mapper_common(self, _status):
    """Maps most common errors
    """
    if Status.DOES_NOT_EXIST in _status or Status.NOT_PUBLISHED in _status:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{_name(self)} not found"
        )
    else:
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"Not enough privileges ({_status})"
        )


def check(
        *allowed_types: Status,
        error_mapper: Callable[[BaseRepo, Status], HTTPException] = _mapper_common,
        force_exists: bool = True
):
    """Generalized check

    Parameters
    ----------
    allowed_types
        Types to be checked for. If any match the result is returned.
    error_mapper
        Mapper for errors.
    force_exists
        IF the resource does not need to exist set this to False

    Returns
    -------
    Function result
    """

    def parameter_decorator(f):
        inject_argument = _check_status_kwarg(f)

        @functools.wraps(f)
        async def actual_decorator(*args, **kwargs):
            status_ = await _exists(*args)

            if inject_argument is not None:
                kwargs = {**kwargs, inject_argument: status_}

            if (not force_exists or Status.EXISTS in status_) and any(map(status_.__contains__, allowed_types)):
                return await f(*args, **kwargs)
            else:
                raise error_mapper(args[0], status_)

        return actual_decorator

    return parameter_decorator


def exists(f):
    """Checks that the resource exists

    Works only on Repo instance methods where the first argument is an identifier for a
    resource the Repo represents

    For example ::

        @exists
        def one(project: PID):
            pass

        @exists
        def two(project: ProjectModel):
            assert hasattr(project, "id")



    Will take the *project* argument and use that for checking *exist* method.
    The method will additionally handle any model parameters by taking their *id* attribute.

    This way the method will only handle existing resources.
    """
    return check(  # pragma: no branch
        Status.EXISTS,
        error_mapper=lambda self, s: HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{_name(self)} not found"
        )
    )(f)  # TODO: Seems to be bugged in coverage, saying didn't jump?


def not_exists(f):
    """Opposite of *exists*.

    Assures the resource in question does not already exist.

    See Also
    --------
    exists:
        More documentation.
    """
    return check(  # pragma: no branch
        Status.DOES_NOT_EXIST,
        error_mapper=lambda self, s: HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"{_name(self)} exists"
        ),
        force_exists=False
    )(f)  # TODO: Seems to be bugged in coverage, saying didn't jump?


def parents(f):
    """Checks just parents

    See Also
    --------
    exists:
        More documentation.
    """
    return check(Status.DOES_NOT_EXIST, Status.EXISTS, force_exists=False)(f)


def admin(f):
    """Check user is admin

    See Also
    --------
    exists:
        More documentation.
    """
    return check(Status.ADMIN, Status.SUPER)(f)


def own(f):
    """Check users own resource

    See Also
    --------
    exists:
        More documentation.
    """
    return check(Status.OWN)(f)


def published_or_admin(f):
    """Check exists and published

    Admins will bypass this as well as users for their personal submissions.

    See Also
    --------
    exists:
        More documentation.
    """
    return check(Status.PUBLISHED, Status.OWN, Status.ADMIN, Status.SUPER)(f)


def own_or_admin(f):
    """Check own or admin

    See Also
    --------
    exists:
        More documentation.
    """
    return check(Status.OWN, Status.ADMIN, Status.SUPER)(f)


def zuper(f):
    """Only Super will pass this

    See Also
    --------
    exists:
        More documentation.
    """
    return check(Status.SUPER, force_exists=True)(f)


__all__ = [
    "exists",
    "not_exists",
    "zuper",
    "admin",
    "own_or_admin",
    "published_or_admin",
    "parents",
    "own"
]
