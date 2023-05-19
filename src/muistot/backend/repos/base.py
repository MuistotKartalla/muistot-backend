from abc import ABC, abstractmethod
from functools import wraps
from typing import List, Any, NoReturn, Optional, Dict

from .status import StatusProvider
from ...database import Database
from ...files import Files
from ...security import User


class BaseRepo(StatusProvider, ABC):
    """
    Base for Repo classes.

    These classes provide data to endpoints.
    Throwing HTTPExceptions is a good way to propagate exceptions.
    """
    db: Database
    lang: str
    user: User
    identifiers: Dict[str, Any]

    def __init__(
            self,
            db: Database,
            lang: str,
            user: User,
            **identifiers: Dict[str, Any]
    ):
        """Inject
        """
        self.db = db
        self.lang = lang
        self.user = user
        self.identifiers = identifiers

    def __getattr__(self, item: str):
        if item in self.identifiers:
            return self.identifiers[item]
        raise AttributeError('Failed to find attribute %r from %r' % (item, type(self).__name__))

    @classmethod
    def from_repo(cls, repo: "BaseRepo") -> "BaseRepo":
        return cls(repo.db, repo.lang, repo.user, **repo.identifiers)

    @abstractmethod
    async def all(self, *args) -> List:
        """
        Return all resources matching arguments.
        """

    @abstractmethod
    async def one(self, *args) -> Any:
        """
        Return a single resource. Return a model class.
        """

    @abstractmethod
    async def create(self, model) -> Any:
        """
        Create a resource. Return identifier on success.
        """

    @abstractmethod
    async def modify(self, *args) -> bool:
        """
        Modify a resource. Return whether the resource changed.
        """

    @abstractmethod
    async def delete(self, *args) -> NoReturn:
        """
        Delete the resource
        """

    @abstractmethod
    async def toggle_publish(self, *args) -> bool:
        """
        Set publish
        """

    @property
    def identity(self) -> Optional[str]:
        return self.user.identity if self.user.is_authenticated else None

    @property
    def authenticated(self) -> bool:
        return self.identity is not None

    @property
    def superuser(self) -> bool:
        return self.user.is_superuser

    @property
    def files(self) -> Files:
        return Files(self.db, self.user)


def append_identifier(identifier: str, *, value: bool = False, key: str = None, literal: Any = None):
    def decorator(f):
        @wraps(f)
        async def wrapper(self: BaseRepo, *args, **kwargs):
            if value:
                self.identifiers[identifier] = args[0]
            elif key:
                self.identifiers[identifier] = getattr(args[0], key)
            else:
                self.identifiers[identifier] = literal
            return await f(self, *args, **kwargs)

        return wrapper

    return decorator
