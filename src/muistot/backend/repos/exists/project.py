from .base import Exists, Status
from ...models import PID


class ProjectExists(Exists):
    project: PID

    _authenticated = (
        """
        SELECT p.published              AS project_published,
               p.admin_posting,
               p.auto_publish,
               l.lang                   AS default_language,
               NOT ISNULL(pa.user_id)   AS is_admin,
               FALSE                    AS is_creator
        FROM projects p
            JOIN languages l on p.default_language_id = l.id
            LEFT JOIN project_admins pa
                    JOIN users u2 ON pa.user_id = u2.id
                        AND u2.username = :user
                 ON p.id = pa.project_id
        WHERE p.name = :project
        """
    )

    _plain = (
        """
        SELECT p.published              AS project_published,
               p.admin_posting,
               p.auto_publish,
               l.lang                   AS default_language,
               FALSE                    AS is_creator
        FROM projects p
            JOIN languages l on p.default_language_id = l.id
        WHERE p.name = :project
        """
    )

    async def exists(self) -> Status:
        if self.authenticated:
            m = await self.db.fetch_one(
                self._authenticated,
                values=dict(project=self.project, user=self.identity),
            )
        else:
            m = await self.db.fetch_one(
                self._plain,
                values=dict(project=self.project),
            )
        if m is not None:
            self._lang = m["default_language"]
            return self.start(m, "project_published")
        else:
            return Status.DOES_NOT_EXIST
