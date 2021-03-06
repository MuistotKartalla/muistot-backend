from abc import ABC, abstractmethod
from enum import Flag, auto
from functools import wraps
from typing import Any, Mapping, Union

from ....database import Database
from ....security import User


def exists(f):
    @wraps(f)
    def check_self(self, *args):
        if Status.DOES_NOT_EXIST not in self:
            return f(self, *args)
        else:
            return self

    return check_self


class Status(Flag):
    EXISTS = auto()
    DOES_NOT_EXIST = auto()
    NOT_PUBLISHED = auto()
    PUBLISHED = auto()
    OWN = auto()
    ADMIN = auto()
    SUPER = auto()
    ADMIN_POSTING = auto()
    AUTO_PUBLISH = auto()

    @property
    def own(self) -> bool:
        return Status.OWN in self

    @property
    def admin(self) -> bool:
        return Status.ADMIN in self or Status.SUPER in self

    @property
    def published(self) -> bool:
        return Status.PUBLISHED in self

    @property
    def pap(self) -> bool:
        return Status.ADMIN_POSTING in self

    @staticmethod
    def start(m: Any) -> "Status":
        """Evaluate if this resource exists
        """
        if m is None:
            return Status.DOES_NOT_EXIST
        else:
            return Status.EXISTS

    @exists
    def add_published(self, m: Mapping, value: Union[int, str]) -> "Status":
        """Add information if this resource is published
        """
        return self | Status.PUBLISHED if m[value] else self | Status.NOT_PUBLISHED

    @exists
    def add_own(self, m: Mapping, value: Union[int, str] = 'is_creator') -> "Status":
        """Add information if this resource is the users own creation
        """
        return self | Status.OWN if m[value] else self

    def add_admin(self, m: Mapping, value: Union[int, str] = 'is_admin') -> "Status":
        """Add information on if this user is an admin
        """
        return self | Status.ADMIN if m is not None and m[value] else self

    def add_pap(self, m: Mapping, value: Union[int, str] = 'admin_posting') -> "Status":
        """Project admin posting
        """
        return self | Status.ADMIN_POSTING if m is not None and m[value] else self

    def add_autopub(self, m: Mapping, value: Union[int, str] = 'auto_publish') -> "Status":
        """Project automatically publishes posting
        """
        return self | Status.AUTO_PUBLISH if m is not None and m[value] else self


class Exists(ABC):
    """Checks resource existence status and any prerequisites
    """
    _plain: str
    _authenticated: str
    _lang: str

    def __init_subclass__(cls, **kwargs):
        """
        Checks Repo requirements and mistakes
        """
        import re
        import inspect
        from ....logging import log
        assert re.fullmatch("^[A-Z][a-z]+(?<!s)Exists$", cls.__name__)
        mro = inspect.getmro(cls)
        if not mro[1] == Exists:
            log.warning(f"{cls.__name__} not inheriting base exists directly")

    def __init__(self, db: Database, user: User, **identifiers):
        """Construct a exist checker

        Constructed automagically by a repo

        Parameters
        ----------
        db
            Database instance
        user
            Current user
        identifiers
            Any related identifiers
        """
        self.db = db
        self._user = user
        for k, v in identifiers.items():
            setattr(self, k, v)

    @property
    def identity(self):
        """Returns the current user identity
        """
        return self._user.identity if self._user.is_authenticated else None

    @property
    def authenticated(self):
        """Returns whether current user is authenticated
        """
        return self.identity is not None

    @abstractmethod
    async def exists(self) -> Status:
        """Checks the existence status for this instance

        This should first check that all prerequisites are filled and throw if not
        and then use the methods from Status to construct a Status.

        Mainly useful for the state decorators.

        Returns
        -------
        status
            Status-instance to check the state of this resource

        Raises
        ------
        fastapi.HTTPException
            On failure to meet prerequisites
        """

    @property
    def default_language(self):
        return getattr(self, "_lang", "fi")

    def start(self, m: Mapping, tag: str) -> Status:
        self._lang = m["default_language"]
        if self.authenticated:
            return Status.start(m[tag]) \
                .add_published(m, tag) \
                .add_pap(m) \
                .add_autopub(m) \
                .add_admin(m) \
                .add_own(m)
        else:
            return Status.start(m[tag]) \
                .add_published(m, tag) \
                .add_pap(m) \
                .add_autopub(m)


__all__ = [
    'Status',
    'Exists'
]
