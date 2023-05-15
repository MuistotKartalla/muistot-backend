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
from ...database import Databases, Database
# noinspection PyUnresolvedReferences
from ...security import require_auth, scopes

DEFAULT_DB = Depends(Databases.default)
