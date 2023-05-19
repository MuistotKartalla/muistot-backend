from typing import Type

from fastapi.params import Depends
from fastapi.requests import Request

from ...repos.base import BaseRepo
from ....middleware.database import DatabaseMiddleware, Database
from ....middleware.language import LanguageMiddleware
from ....middleware.session import SessionMiddleware, User


class Repo(Depends):

    def __init__(self, repo: Type[BaseRepo]):
        super(Repo, self).__init__(dependency=self.construct)
        self.repo_class = repo

    def construct(
            self,
            request: Request,
            db: Database = Depends(DatabaseMiddleware.default),
            user: User = Depends(SessionMiddleware.user),
            lang: str = Depends(LanguageMiddleware.get),
    ):
        return self.repo_class(
            db=db,
            user=user,
            lang=lang,
            **request.path_params,
        )
