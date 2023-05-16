# noinspection PyUnresolvedReferences
from textwrap import dedent

from fastapi import Depends
# noinspection PyUnresolvedReferences
from fastapi import Request, Response

# noinspection PyUnresolvedReferences
from .utils import *
# noinspection PyUnresolvedReferences
from ..models import *
# noinspection PyUnresolvedReferences
from ..repos import *
# noinspection PyUnresolvedReferences
from ...database import Database
# noinspection PyUnresolvedReferences
from ...security import require_auth, scopes


async def _default_db(r: Request) -> Database:
    async with r.state.databases.default() as db:
        yield db


DEFAULT_DB = Depends(_default_db)
