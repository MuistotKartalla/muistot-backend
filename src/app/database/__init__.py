from threading import Lock
from typing import NoReturn, Generator

from aiomysql import IntegrityError as IELow
from aiomysql import InternalError, OperationalError
from databases import Database
from fastapi import HTTPException, Depends

instance_lock = Lock()
instance: Database
rollback: bool

old_instance_lock = Lock()
old_instance: Database


class IntegrityError(HTTPException):
    """
    Higher level entity representing an integrity violation.

    This exception is something that should be caught and handled
    to provide a more specific error message
    """

    def __init__(self) -> NoReturn:
        super().__init__(400, "Integrity violation")


async def init_database(url: str, persist: bool = False, **options) -> NoReturn:
    """
    Initialize a database connection

    https://www.encode.io/databases/connections_and_transactions/
    :param url:         Database Connection URL
    :param persist:     Whether to force rollbacks for this connection
    :param options:     Other vendor specific options to the driver
    """
    global instance
    global rollback
    with instance_lock:
        rollback = not persist
        instance = Database(url, **options)
        try:
            await instance.connect()
        except (InternalError, OperationalError):
            # This should be safely ignored as this could prevent the whole
            # application from starting up. The database might simply not
            # be available at this time.
            pass
    # TODO: Deprecated
    global old_instance
    with old_instance_lock:
        rollback = not persist
        old_instance = Database(url.rsplit('/')[0] + "/muistotkartalla", **options)
        try:
            await old_instance.connect()
        except (InternalError, OperationalError):
            # This should be safely ignored as this could prevent the whole
            # application from starting up. The database might simply not
            # be available at this time.
            pass


async def dba() -> Generator[Database, None, None]:
    """
    Returns the current Database instance with an open transaction

    :raises IntegrityError:  on integrity violations
    :return: Generator for database transactions
    """
    global instance
    try:
        with instance_lock:
            if not instance.is_connected:
                await instance.connect()
            async with instance.transaction(force_rollback=rollback):
                yield instance
    except (InternalError, OperationalError):
        # These are serious
        raise HTTPException(503, 'Database Error')
    except IELow:
        raise IntegrityError


async def dbb() -> Generator[Database, None, None]:
    """
    Returns the current Database instance with an open transaction

    TODO: Deprecated
    :raises IntegrityError:  on integrity violations
    :return: Generator for database transactions
    """
    global old_instance
    try:
        with old_instance_lock:
            if not old_instance.is_connected:
                await old_instance.connect()
            async with old_instance.transaction(force_rollback=rollback):
                yield old_instance
    except (InternalError, OperationalError):
        # These are serious
        raise HTTPException(503, 'Database Error')
    except IELow:
        raise IntegrityError


async def close() -> NoReturn:
    """
    Closes the current database
    """
    try:
        await instance.disconnect()
    except (InternalError, OperationalError):
        # Don't care
        pass
    # TODO: Deprecated
    try:
        await old_instance.disconnect()
    except (InternalError, OperationalError):
        # Don't care
        pass


async def start() -> NoReturn:
    """
    Starts the database
    """
    from ..config import Config
    db = Config.db
    url = f'mysql://{db.user}:{db.password}@{db.host}:{db.port}/{db.database}'
    test: str = Config.testing
    await init_database(url, persist=not test, ssl=True, min_size=1, max_size=10, charset='utf8mb4')


__all__ = ['start', 'dba', 'dbb', 'Database', 'Depends', 'IntegrityError', 'close']
