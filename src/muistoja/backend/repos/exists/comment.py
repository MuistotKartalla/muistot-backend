from typing import Optional

from fastapi import HTTPException, status

from .base import Exists, Status
from ...models import PID, SID, MID, CID


class CommentExists(Exists):
    project: PID
    site: SID
    memory: MID
    comment: Optional[CID]

    _authenticated = (
        """
        SELECT p.published,
               s.published,
               m.published,
               c.published,
               u.username = :user,
               NOT ISNULL(pa.user_id)
        FROM projects p
                 LEFT JOIN sites s ON p.id = s.project_id
            AND s.name = :site
                 LEFT JOIN memories m ON s.id = m.site_id
            AND m.id = :memory
                 LEFT JOIN comments c 
                        JOIN users u ON c.user_id = u.id
                    ON m.id = c.memory_id
            AND c.id = :comment
                 LEFT JOIN project_admins pa
                    JOIN users u2 ON pa.user_id = u2.id
                        AND u2.username = :user
                 ON p.id = pa.project_id
        WHERE p.name = :project
        """
    )

    _plain = (
        """
        SELECT p.published, 
               s.published,
               m.published,
               c.published
        FROM projects p
                 LEFT JOIN sites s ON p.id = s.project_id
            AND s.name = :site
                 LEFT JOIN memories m ON s.id = m.site_id
            AND m.id = :memory
                 LEFT JOIN comments c ON m.id = c.memory_id
            AND c.id = :comment
        WHERE p.name = :project
        """
    )

    async def exists(self) -> Status:
        if self.authenticated:
            m = await self.db.fetch_one(
                self._authenticated,
                values=dict(
                    comment=self.comment,
                    memory=self.memory,
                    site=self.site,
                    project=self.project,
                    user=self.identity,
                ),
            )
        else:
            m = await self.db.fetch_one(
                self._plain,
                values=dict(
                    comment=self.comment,
                    memory=self.memory,
                    site=self.site,
                    project=self.project,
                ),
            )

        if m is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        elif m[1] is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
        elif m[2] is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

        s: Status = Status.start(m[3]).add_published(m, 3)

        if self.authenticated:
            s = s.add_admin(m, 5).add_own(m, 4)

        if s.own or s.admin:
            return s

        if m[0] == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        elif m[1] == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
        elif m[2] == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

        return s
