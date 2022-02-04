from typing import Set, Optional

from pydantic import BaseModel, Field
from starlette.authentication import BaseUser

from .scopes import *


class User(BaseModel, BaseUser):
    """
    Base class used for users in the current application.
    """
    token: Optional[bytes]
    username: Optional[str]
    scopes: Set[str] = Field(default_factory=lambda: set())
    admin_projects: Set[str] = Field(default_factory=lambda: set())

    def __init__(self, username: Optional[str] = None, token: Optional[bytes] = None):
        if username is not None:
            super(User, self).__init__(username=username, scopes={AUTHENTICATED}, token=token)
            self.token = token
        else:
            super(User, self).__init__()

    @property
    def is_superuser(self) -> bool:
        return SUPERUSER in self.scopes

    @property
    def identity(self) -> str:
        return self.username or '! not authenticated !'

    @property
    def display_name(self) -> str:
        return self.identity

    @property
    def is_authenticated(self) -> bool:
        return AUTHENTICATED in self.scopes

    def is_admin_in(self, project: str) -> bool:
        return project in self.admin_projects or self.is_superuser


__all__ = [
    'User'
]
