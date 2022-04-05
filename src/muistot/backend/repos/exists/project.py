from .base import Exists, Status
from ...models import PID


class ProjectExists(Exists):
    project: PID

    _authenticated = (
        """
        SELECT p.published,
               NOT ISNULL(pa.user_id)
        FROM projects p
            LEFT JOIN project_admins pa
                    JOIN users u2 ON pa.user_id = u2.id
                        AND u2.username = :user
                 ON p.id = pa.project_id
        WHERE p.name = :project
        """
    )

    _plain = (
        """
        SELECT published 
        FROM projects 
        WHERE name = :project
        """
    )

    async def exists(self) -> Status:
        if self.authenticated:
            m = await self.db.fetch_one(
                self._authenticated,
                values=dict(project=self.project, user=self.identity),
            )
            s = Status.start(m)
            s = s.add_published(m, 0)
            return s.add_admin(m, 1)
        else:
            m = await self.db.fetch_one(
                self._plain,
                values=dict(project=self.project),
            )
            return Status.start(m).add_published(m, 0)
