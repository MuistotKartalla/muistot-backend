from typing import Optional, Mapping

from starlette.exceptions import HTTPException
from starlette.status import HTTP_404_NOT_FOUND

from .base import StatusProvider, Status
from ...models import PID, SID


class SiteStatus(StatusProvider):
    project: PID
    site: Optional[SID]

    @property
    def query_authenticated(self) -> str:
        return (
            """
            SELECT p.published              AS project_published,
                   p.admin_posting,
                   p.auto_publish,
                   NOT ISNULL(pa.user_id)   AS is_admin,
                   s.published              AS site_published,
                   s.id IS NOT NULL         AS site_exists,
                   uc.username = :user      AS is_creator
            FROM projects p
                    LEFT JOIN sites s 
                        ON p.id = s.project_id AND s.name = :site
                    LEFT JOIN project_admins pa
                            JOIN users u2 ON pa.user_id = u2.id AND u2.username = :user
                        ON p.id = pa.project_id
                    LEFT JOIN users uc 
                        ON uc.id = s.creator_id
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
                   s.id IS NOT NULL         AS site_exists
            FROM projects p
                     LEFT JOIN sites s
                        ON p.id = s.project_id
                AND s.name = :site
            WHERE p.name = :project
            """
        )

    async def derive_status(self, m: Mapping) -> Status:
        if m is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Project not found")

        s = Status.construct(m, {
            "site_exists": (
                Status.EXISTS,
                Status.DOES_NOT_EXIST,
            ),
            "site_published": (
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

        if Status.ADMIN not in s and not m["project_published"]:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Project not found")
        else:
            return s
