from typing import List, Dict

from ...database import Database
from ...security.scopes import SUPERUSER, ADMIN


async def is_superuser(username: str, db: Database) -> bool:
    return (await db.fetch_val(
        """
        SELECT EXISTS(
            SELECT 1 
            FROM users u 
                JOIN superusers su on su.user_id = u.id
            WHERE u.username = :user
        )
        """,
        values=dict(user=username),
    )) == 1


async def admin_in(username: str, db: Database) -> List[str]:
    return [m[0] for m in await db.fetch_all(
        """
        SELECT p.name
        FROM users u
            JOIN project_admins pa on u.id = pa.user_id
            JOIN projects p on pa.project_id = p.id
        WHERE u.username = :user
        """,
        values=dict(user=username),
    )]


async def load_session_data(username: str, db: Database) -> Dict:
    """Loads user specific session data

    Returns the session data as

    - Scopes:   List of Auth scopes
    - Projects: List of Admin projects
    """
    scopes = set()
    if await is_superuser(username, db):
        scopes.add(SUPERUSER)
        scopes.add(ADMIN)
    admin_in_projects = await admin_in(username, db)
    if len(admin_in_projects) > 0:
        scopes.add(ADMIN)
        return dict(scopes=list(scopes), projects=admin_in_projects)
    else:
        return dict(scopes=list(scopes), projects=list())


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


def hash_token(token: str):
    from hashlib import sha256
    return sha256(token.encode("ascii")).digest().hex()


async def check_token(username: str, token: str, db: Database) -> bool:
    from secrets import compare_digest
    try:
        token = hash_token(token)
        in_database = await fetch_verifier(username, db)
        if in_database is not None and compare_digest(token, in_database):
            return True
    except UnicodeEncodeError:
        pass
    return False


def create_code():
    import string
    import secrets
    return "".join(secrets.choice(string.digits) for _ in range(0, 6))


__all__ = [
    "load_session_data",
    "check_token",
    "hash_token",
    "create_code"
]
