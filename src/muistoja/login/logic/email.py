from secrets import token_urlsafe
from typing import Tuple, Optional

from databases import Database

from ...mailer import get_mailer


async def create_email_verifier(username: str, db: Database) -> Tuple[str, str, bool]:
    token = token_urlsafe(150)
    await db.execute(
        """
        DELETE FROM user_email_verifiers WHERE user_id = (SELECT id FROM users WHERE username = :user)
        """,
        values=dict(user=username)
    )
    m = await db.fetch_one(
        """
        REPLACE INTO user_email_verifiers (user_id, verifier) 
        SELECT id, :token 
        FROM users
        WHERE username = :user
        RETURNING (SELECT email FROM users WHERE id=user_id), (SELECT verified FROM users WHERE id=user_id) 
        """,
        values=dict(user=username, token=token),
    )
    return m[0], token, m[1]


async def send_email(username: str, db: Database):
    email, token, verified = await create_email_verifier(username, db)
    mailer = get_mailer()
    await mailer.send_email(email, user=username, token=token, verified=verified)


async def can_send_email(email: str, db: Database):
    return (await db.fetch_val(
        """
        SELECT EXISTS(
            SELECT 1
            FROM user_email_verifiers uev 
                JOIN users u on uev.user_id = u.id 
            WHERE email = :email AND TIMESTAMPDIFF(MINUTE, uev.created_at, CURRENT_TIMESTAMP) < 5
        )
        """,
        values=dict(email=email),
    )) == 0


async def fetch_user_by_email(email: str, db: Database) -> Optional[str]:
    return await db.fetch_val(
        """
        SELECT username FROM users WHERE email = :email
        """,
        values=dict(email=email),
    )


__all__ = [
    'send_email',
    'can_send_email',
    'fetch_user_by_email'
]