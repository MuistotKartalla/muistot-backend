from databases import Database
from fastapi import HTTPException


class IntegrityError(HTTPException):
    """
    Higher level entity representing an integrity violation.

    This exception is something that should be caught and handled
    to provide a more specific error message
    """

    def __init__(self):
        super().__init__(409, "Integrity violation")


class DatabaseConnection:
    db: Database

    def __init__(
            self,
            url: str,
            ssl: bool,
            min_connections: int = 1,
            max_connections: int = 100
    ):
        self.db = Database(
            url,
            ssl=ssl,
            min_size=min_connections,
            max_size=max_connections,
            charset="utf8mb4"
        )

    async def connect(self):
        await self.db.connect()

    async def disconnect(self):
        await self.db.disconnect()

    async def __call__(self):
        async with self.db as db:
            async with db.connection() as conn:
                async with conn.transaction():
                    yield conn
