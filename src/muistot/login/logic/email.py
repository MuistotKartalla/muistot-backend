from typing import Tuple, Optional

from .data import hash_token, create_token
from ...database import Database

async def fetch_verifier(username: str, db: Database) -> str:
    return await db.fetch_val(
        """
        SELECT uev.verifier
        FROM user_email_verifiers uev 
            JOIN users u ON uev.user_id = u.id
                AND u.username = :user
        WHERE TIMESTAMPDIFF(MINUTE, uev.created_at, CURRENT_TIMESTAMP) < 10
        """,
        values=dict(user=username),
    )


async def create_email_verifier(username: str, db: Database) -> Tuple[str, str, bool]:
    token = create_token()
    await db.execute(
        """
        INSERT INTO user_email_verifiers (user_id, verifier) 
            SELECT id, :token 
            FROM users
            WHERE username = :user
        ON DUPLICATE KEY UPDATE verifier = :token
        """,
        values=dict(user=username, token=hash_token(token)),
    )
    m = await db.fetch_one(
        """
        SELECT email, verified FROM users WHERE username = :user
        """,
        values=dict(user=username),
    )
    return m[0], token, m[1]


async def can_send_email(email: str, db: Database):
    return bool(await db.fetch_val(
        """
        SELECT NOT EXISTS(
            SELECT 1
            FROM user_email_verifiers uev 
                JOIN users u ON uev.user_id = u.id 
            WHERE u.email = :email AND TIMESTAMPDIFF(MINUTE, uev.created_at, CURRENT_TIMESTAMP) < 5
        )
        """,
        values=dict(email=email),
    ))


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


async def delete_verifiers(username: str, db: Database):
    await db.execute(
        """
        DELETE FROM user_email_verifiers 
        WHERE user_id = (SELECT id FROM users WHERE username = :user)
        """,
        values=dict(user=username),
    )
