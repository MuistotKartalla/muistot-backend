from fastapi import Depends, Request

from ...database import Database


async def default_database(r: Request) -> Database:
    async with r.state.databases.default() as db:
        yield db


DEFAULT_DB = Depends(default_database)
