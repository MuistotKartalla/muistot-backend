from typing import List, Dict

import headers
from fastapi import Response, status

from ...database import Database
from ...security import Session, SessionManager
from ...security.scopes import SUPERUSER, ADMIN


async def is_superuser(username: str, db: Database) -> bool:
    return (await db.fetch_val(
        """
        SELECT EXISTS(
            SELECT 1 
            FROM users u 
                JOIN superusers su ON su.user_id = u.id
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
            JOIN project_admins pa ON u.id = pa.user_id
            JOIN projects p ON pa.project_id = p.id
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


async def start_session(username: str, db: Database, sm: SessionManager) -> Response:
    token = sm.start_session(
        Session(
            user=username,
            data=await load_session_data(username, db)
        )
    )
    await db.execute(
        """
        CALL log_login(:user)
        """,
        values=dict(user=username),
    )
    return Response(
        status_code=status.HTTP_200_OK,
        headers={headers.AUTHORIZATION: f"bearer {token}"},
    )
