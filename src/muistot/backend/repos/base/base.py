import inspect
import re
from abc import ABC, abstractmethod
from typing import List, Any, NoReturn, Union, Optional, Dict

from ....database import Database
from ....files import Files
from ....logging import log
from ....security import User


class BaseRepo(ABC):
    """
    Base for Repo classes.

    These classes provide data to endpoints.
    Throwing HTTPExceptions is a good way to propagate exceptions.
    """
    lang: str
    user: User

    def __init_subclass__(cls, **kwargs):
        """
        Checks Repo requirements and mistakes
        """

        resource = cls.__name__.removesuffix("Repo").lower()
        assert re.fullmatch("^[A-Z][a-z]+(?<!s)Repo$", cls.__name__)

        mro = inspect.getmro(cls)
        if not mro[1] == BaseRepo:
            log.warning(f"{cls.__name__} not inheriting base repo directly")
        funcs = mro[0].__dict__
        for name in ["_check_exists", "_check_not_exists"]:
            assert name not in funcs
        for name in [f"construct_{resource}"]:
            if name not in funcs:
                log.warning(f"No {name} declared in repo {cls.__name__}")

    def __init__(self, db: Database, **kwargs):
        self.db = db
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.kwargs = dict(**kwargs)
        self.user: Union[User] = User.null()

    def configure(self, user: User, language: str) -> "BaseRepo":
        """
        Adds configuration data from the Request to this repo

        Adds:

        - User
        - Language
        """
        self.user = user
        self.lang = language
        return self

    def from_repo(self, repo: "BaseRepo") -> "BaseRepo":
        self.user = repo.user
        self.lang = repo.lang
        return self

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

    @property
    def identifiers(self) -> Dict[str, Any]:
        return dict(**self.kwargs)


__all__ = [
    "BaseRepo",
]
