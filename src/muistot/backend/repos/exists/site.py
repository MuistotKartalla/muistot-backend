from typing import Optional

from fastapi import HTTPException, status

from .base import Exists, Status
from ...models import PID, SID


class SiteExists(Exists):
    project: PID
    site: Optional[SID]

    _authenticated = (
        """
        SELECT p.published              AS project_published,
               p.admin_posting,
               p.auto_publish,
               NOT ISNULL(pa.user_id)   AS is_admin,
               s.published              AS site_published,
               uc.username = :user      AS is_creator
        FROM projects p
                LEFT JOIN sites s ON p.id = s.project_id
            AND s.name = :site
                LEFT JOIN project_admins pa
                    JOIN users u2 ON pa.user_id = u2.id
                        AND u2.username = :user
                 ON p.id = pa.project_id
                 LEFT JOIN users uc ON uc.id = s.creator_id
        WHERE p.name = :project
        """
    )

    _plain = (
        """
        SELECT p.published              AS project_published,
               p.admin_posting,
               p.auto_publish,
               s.published              AS site_published
        FROM projects p
                 LEFT JOIN sites s ON p.id = s.project_id
            AND s.name = :site
        WHERE p.name = :project
        """
    )

    async def exists(self) -> Status:
        if self.authenticated:
            m = await self.db.fetch_one(
                self._authenticated,
                values=dict(site=self.site, project=self.project, user=self.identity),
            )
        else:
            m = await self.db.fetch_one(
                self._plain,
                values=dict(site=self.site, project=self.project),
            )

        if m is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        s: Status = self.start(m, "site_published")

        if s.own or s.admin:
            return s

        if not m["project_published"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        return s
