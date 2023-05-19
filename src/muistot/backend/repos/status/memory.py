from typing import Optional, Mapping

from starlette.exceptions import HTTPException
from starlette.status import HTTP_404_NOT_FOUND

from .base import StatusProvider, Status
from ...models import PID, SID, MID


class MemoryStatus(StatusProvider):
    project: PID
    site: SID
    memory: Optional[MID]

    @property
    def query_authenticated(self) -> str:
        return (
            """
            SELECT p.published              AS project_published,
                   p.admin_posting,
                   p.auto_publish,
                   NOT ISNULL(pa.user_id)   AS is_admin,
                   s.published              AS site_published,
                   m.published              AS memory_published,
                   m.id IS NOT NULL         AS memory_exists,
                   u.username = :user       AS is_creator
            FROM projects p
                     LEFT JOIN sites s 
                        ON p.id = s.project_id AND s.name = :site
                     LEFT JOIN memories m 
                            JOIN users u ON m.user_id = u.id
                        ON s.id = m.site_id AND m.id = :memory
                     LEFT JOIN project_admins pa
                            JOIN users u2 ON pa.user_id = u2.id AND u2.username = :user
                        ON p.id = pa.project_id
            WHERE p.name = :project
            """
        )

    @property
    def query_anonymous(self) -> str:
        return (
            """
            SELECT p.published              AS project_published,
                   p.admin_posting,
                   p.auto_publish,
                   s.published              AS site_published,
                   m.published              AS memory_published,
                   m.id IS NOT NULL         AS memory_exists
            FROM projects p
                     LEFT JOIN sites s 
                        ON p.id = s.project_id AND s.name = :site
                     LEFT JOIN memories m 
                        ON s.id = m.site_id AND m.id = :memory
            WHERE p.name = :project
            """
        )

    async def derive_status(self, m: Mapping) -> Status:
        if m is None:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        elif m["site_published"] is None:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="Site not found",
            )

        s = Status.construct(m, {
            "memory_exists": (
                Status.EXISTS,
                Status.DOES_NOT_EXIST,
            ),
            "memory_published": (
                Status.PUBLISHED,
                Status.NOT_PUBLISHED,
            ),
            "admin_posting": (
                Status.ADMIN_POSTING,
                Status.NONE,
            ),
            "auto_publish": (
                Status.AUTO_PUBLISH,
                Status.NONE,
            ),
            "is_admin": (
                Status.ADMIN,
                Status.NONE,
            ),
            "is_creator": (
                Status.OWN,
                Status.NONE,
            ),
        })

        if Status.ADMIN not in s:
            if not m["project_published"]:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND, detail="Project not found"
                )
            elif not m["site_published"]:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND, detail="Site not found"
                )
        return s
