from fastapi import Depends

from ...middleware import DatabaseMiddleware

DEFAULT_DB = Depends(DatabaseMiddleware.default)
