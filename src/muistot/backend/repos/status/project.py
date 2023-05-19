from typing import Mapping

from .base import StatusProvider, Status
from ...models import PID


class ProjectStatus(StatusProvider):
    project: PID

    @property
    def query_authenticated(self) -> str:
        return (
            """
            SELECT p.published              AS project_published,
                   TRUE                     AS project_exists,
                   p.admin_posting,
                   p.auto_publish,
                   NOT ISNULL(pa.user_id)   AS is_admin,
                   FALSE                    AS is_creator
            FROM projects p
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
                   TRUE                     AS project_exists,
                   p.admin_posting,
                   p.auto_publish,
                   FALSE                    AS is_creator
            FROM projects p
            WHERE p.name = :project
            """
        )

    async def derive_status(self, m: Mapping) -> Status:
        return Status.construct(m, {
            "project_exists": (
                Status.EXISTS,
                Status.DOES_NOT_EXIST,
            ),
            "project_published": (
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
