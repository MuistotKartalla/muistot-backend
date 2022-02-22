from threading import Lock

from aiomysql import OperationalError as ConnectionError

from .connection import DatabaseConnection
from ..logging import log

LOCK = Lock()
STORE = dict()


def get_database(config_name: str) -> DatabaseConnection:
    with LOCK:
        from ..config import config_to_url, Config
        cfg = Config.db[config_name]
        url = config_to_url(cfg)
        db = DatabaseConnection(url=url, ssl=cfg.use_ssl)
        STORE[config_name] = db
        return db


async def connect():
    with LOCK:
        for k, db in STORE.items():
            try:
                await db.disconnect()
            except ConnectionError as e:
                log.info(f"Failed to disconnect database: {k}", exc_info=e)


async def disconnect():
    with LOCK:
        for k, db in STORE.items():
            try:
                await db.disconnect()
            except ConnectionError as e:
                log.info(f"Failed to disconnect database: {k}", exc_info=e)


default_database = get_database("default")
