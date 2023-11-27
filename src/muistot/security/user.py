from typing import Set, Optional

from pydantic import BaseModel, Field
from starlette.authentication import BaseUser

from .scopes import *


class User(BaseModel, BaseUser):
    """
    Base class used for users in the current application.
    """

    token: Optional[str]
    username: Optional[str]
    scopes: Set[str] = Field(default_factory=lambda: set())
    admin_projects: Set[str] = Field(default_factory=lambda: set())
    moderator_projects : Set[str] = Field(default_factory=lambda: set())

    @classmethod
    def from_cache(cls, *, username: str, token: str) -> 'User':
        return User.construct(username=username, token=token, scopes={AUTHENTICATED})

    @classmethod
    def null(cls) -> 'User':
        return User.construct()

    @property
    def is_superuser(self) -> bool:
        return SUPERUSER in self.scopes

    @property
    def identity(self) -> str:
        if self.is_authenticated:
            return self.username
        else:
            raise ValueError()

    @property
    def display_name(self) -> str:
        return self.identity

    @property
    def is_authenticated(self) -> bool:
        return AUTHENTICATED in self.scopes

    def is_admin_in(self, project: str) -> bool:
        return project in self.admin_projects or self.is_superuser

    def is_moderator_in(self, project: str) -> bool:
        return project in self.moderator_projects or self.is_superuser


__all__ = ["User"]
