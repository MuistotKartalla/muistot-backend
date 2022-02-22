# noinspection PyUnresolvedReferences
from textwrap import dedent

# noinspection PyUnresolvedReferences
from databases import Database
# noinspection PyUnresolvedReferences
from fastapi import Request, Response

# noinspection PyUnresolvedReferences
from .utils import *
# noinspection PyUnresolvedReferences
from ..models import *
# noinspection PyUnresolvedReferences
from ..repos import *
# noinspection PyUnresolvedReferences
from ...security import require_auth, scopes


def _database():
    from ...database import dba
    from fastapi import Depends

    return Depends(dba)


DEFAULT_DB = _database()
