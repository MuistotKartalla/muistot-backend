from typing import NoReturn, List

from .connections import Database
from ..models import *


async def fetch_projects(db: Database) -> List[Project]:
    pass


async def fetch_project(name: str, db: Database) -> Project:
    pass


async def create_project(new_project: Project) -> NoReturn:
    pass
