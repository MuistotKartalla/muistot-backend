from aiomysql import IntegrityError as IELow
from aiomysql import InternalError, OperationalError
from databases import Database
from fastapi import HTTPException

from ..config import Config
from ..database import IntegrityError


async def old_db():
    if "old" in Config.db:
        try:
            db = Config.db["old"]
            url = f'mysql://{db.user}:{db.password}@{db.host}:{db.port}/{db.database}'
            async with Database(url) as instance:
                async with instance.transaction(force_rollback=Config.testing):
                    yield instance
        except (InternalError, OperationalError):
            # These are serious
            raise HTTPException(503, 'Database Error')
        except IELow:
            raise IntegrityError
    else:
        yield None
