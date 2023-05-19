from typing import Optional

from ...database import Database


async def fetch_user_by_email(email: str, db: Database) -> Optional[str]:
    return await db.fetch_val(
        """
        SELECT username FROM users WHERE email = :email
        """,
        values=dict(email=email),
    )


async def is_verified(username: str, db: Database) -> bool:
    return await db.fetch_val(
        """
        SELECT verified FROM users WHERE username = :user
        """,
        values=dict(user=username)
    )


async def verify(username: str, db: Database):
    await db.execute(
        """
        UPDATE users SET verified = 1 WHERE username = :user
        """,
        values=dict(user=username)
    )
