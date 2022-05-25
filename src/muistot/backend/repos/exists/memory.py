from typing import Optional

from fastapi import HTTPException, status

from .base import Exists, Status
from ...models import PID, SID, MID


class MemoryExists(Exists):
    project: PID
    site: SID
    memory: Optional[MID]

    _authenticated = (
        """
        SELECT p.published              AS project_published,
               p.admin_posting,
               p.auto_publish,
               l.lang                   AS default_language,
               NOT ISNULL(pa.user_id)   AS is_admin,
               s.published              AS site_published,
               m.published              AS memory_published,
               u.username = :user       AS is_creator
        FROM projects p
            JOIN languages l on p.default_language_id = l.id
                 LEFT JOIN sites s ON p.id = s.project_id
            AND s.name = :site
                 LEFT JOIN memories m
                    JOIN users u ON m.user_id = u.id
                 ON s.id = m.site_id
            AND m.id = :memory
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
               s.published              AS site_published,
               m.published              AS memory_published
        FROM projects p
            JOIN languages l on p.default_language_id = l.id
                 LEFT JOIN sites s ON p.id = s.project_id
            AND s.name = :site
                 LEFT JOIN memories m ON s.id = m.site_id
            AND m.id = :memory
        WHERE p.name = :project
        """
    )

    async def exists(self) -> Status:
        if self.authenticated:
            m = await self.db.fetch_one(
                self._authenticated,
                values=dict(
                    memory=self.memory,
                    site=self.site,
                    project=self.project,
                    user=self.identity,
                ),
            )
        else:
            m = await self.db.fetch_one(
                self._plain,
                values=dict(memory=self.memory, site=self.site, project=self.project),
            )

        if m is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )
        elif m["site_published"] is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Site not found"
            )

        s = self.start(m, "memory_published")

        if s.own or s.admin:
            return s

        if not m["project_published"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )
        elif not m["site_published"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Site not found"
            )

        return s
