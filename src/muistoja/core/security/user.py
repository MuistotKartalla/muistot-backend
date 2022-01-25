from typing import Set, Optional

from pydantic import BaseModel, Field
from starlette.authentication import BaseUser

from . import scopes


class User(BaseModel, BaseUser):
    username: Optional[str]
    scopes: Set[str] = Field(default_factory=lambda: set())
    admin_projects: Set[str] = Field(default_factory=lambda: set())

    @property
    def is_superuser(self) -> bool:
        return scopes.SUPERUSER in self.scopes

    @property
    def identity(self) -> str:
        return self.username or '! not authenticated !'

    @property
    def display_name(self) -> str:
        return self.identity

    @property
    def is_authenticated(self) -> bool:
        return scopes.AUTHENTICATED in self.scopes

    def is_admin_in(self, project: str) -> bool:
        """
        This should be faster than querying DB every time we need to check if someone is an Admin.
        Only verifying from DB should be ok, but initial rejection based on JWT should save time.

        :param project: PID
        :return: Bool
        """
        return project in self.admin_projects or self.is_superuser


__all__ = [
    'User'
]
