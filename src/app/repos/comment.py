from .utils import *


class CommentRepo(BaseRepo):
    project: PID
    site: SID
    memory: MID

    _select = (
        """
        SELECT c.id,
               u.username AS user,
               c.comment,
               c.modified_at
        FROM comments c
                 JOIN memories m ON c.memory_id = m.id
            AND m.id = :memory
                 JOIN sites s ON m.site_id = s.id
            AND s.name = :site
                 JOIN projects p ON s.project_id = p.id
            AND p.name = :project
                 JOIN users u ON c.user_id = u.id
        WHERE c.published
        """
    )

    _select_for_user = (
        """
        SELECT c.id,
               u.username                                         AS user,
               c.comment,
               c.modified_at,
               IF(u2.id IS NOT NULL, NOT c.published, NULL)       AS waiting_approval
        FROM comments c
                 JOIN memories m ON c.memory_id = m.id
            AND m.id = :memory
                 JOIN sites s ON m.site_id = s.id
            AND s.name = :site
                 JOIN projects p ON s.project_id = p.id
            AND p.name = :project
                 JOIN users u ON c.user_id = u.id
                 LEFT JOIN users u2 ON c.user_id = u2.id
                    AND u2.username = :user
        WHERE (c.published OR u.username = :user)
        """
    )

    _select_for_admin = (
        """
        SELECT c.id,
               u.username AS user,
               c.comment,
               c.modified_at,
               IF(c.published, NULL, 1)       AS waiting_approval
        FROM comments c
                 JOIN memories m ON c.memory_id = m.id
            AND m.id = :memory
                 JOIN sites s ON m.site_id = s.id
            AND s.name = :site
                 JOIN projects p ON s.project_id = p.id
            AND p.name = :project
                 JOIN users u ON c.user_id = u.id
        WHERE TRUE
        """
    )

    async def _exists(self, comment: CID) -> Status:
        if self.has_identity:
            m = await self.db.fetch_one(
                """
                SELECT p.published,
                       s.published,
                       m.published,
                       c.published,
                       u.username,
                       ISNULL(pa.user_id)
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
                """,
                values=dict(
                    comment=comment,
                    memory=self.memory,
                    site=self.site,
                    project=self.project,
                    user=self.identity
                )
            )
        else:
            m = await self.db.fetch_one(
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
                """,
                values=dict(comment=comment, memory=self.memory, site=self.site, project=self.project)
            )

        if m is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')
        elif m[1] is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Site not found')
        elif m[2] is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Memory not found')

        s = Status.resolve(m[3])

        _s = self._saoh(m, s, 5, 4)
        if _s is not None:
            return _s

        if m[0] == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')
        elif m[1] == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Site not found')
        elif m[2] == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Memory not found')

        return s

    @staticmethod
    def construct_comment(m) -> Comment:
        return Comment(**m)

    def __init__(self, db: Database, project: PID, site: SID, memory: MID):
        super().__init__(db, project=project, site=site, memory=memory)

    @check_parents
    async def all(self, *, _status: Status) -> List[Comment]:
        values = dict(site=self.site, project=self.project, memory=self.memory)
        if _status == Status.ADMIN:
            sql = self._select_for_admin
        elif self.has_identity:
            sql = self._select_for_user
            values.update(user=self.identity)
        else:
            sql = self._select
        return [self.construct_comment(m) async for m in self.db.iterate(
            sql,
            values=values
        ) if m is not None]

    @check_published_or_admin
    async def one(self, comment: CID, *, _status: Status) -> Comment:
        values = dict(site=self.site, project=self.project, memory=self.memory, comment=comment)
        if _status == Status.ADMIN:
            sql = self._select_for_admin
        elif self.has_identity:
            sql = self._select_for_user
            values.update(user=self.identity)
        else:
            sql = self._select
        return self.construct_comment(await self.db.fetch_one(
            sql + ' AND c.id = :comment',
            values=values
        ))

    @check_parents
    async def create(self, model: NewComment) -> CID:
        return await self.db.fetch_val(
            """
            INSERT INTO comments (memory_id, user_id, comment, published)
            SELECT m.id,
                   u.id,
                   :comment,
                   :published
            FROM memories m
                     JOIN users u ON u.username = :user
            WHERE m.id = :memory
            RETURNING id
            """,
            values=dict(memory=self.memory, user=self.identity, comment=model.comment, published=self.auto_publish)
        )

    @check_own
    async def modify(self, comment: CID, model: ModifiedComment) -> bool:
        await self.db.fetch_val(
            """
            UPDATE comments 
            SET comment=:comment, published=DEFAULT
            WHERE id = :id
            """,
            values=dict(id=comment, comment=model.comment)
        )
        return await self.db.fetch_val("SELECT ROW_COUNT()") != 0

    @check_own_or_admin
    async def delete(self, comment: CID):
        await self.db.fetch_val(
            """
            DELETE c FROM comments c
            JOIN users u ON c.user_id = u.id
                AND u.username = :user
            WHERE c.id = :cid 
            """,
            values=dict(user=self.identity, cid=comment)
        )

    @check_admin
    async def toggle_publish(self, comment: CID, published: bool):
        await self._set_published(published, id=comment)

    @check_parents
    async def by_user(self, user: str) -> List[UserComment]:
        if await self.db.fetch_val(
                "SELECT EXISTS(SELECT 1 FROM users WHERE username = :user)",
                values=dict(user=user)
        ) != 1:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
        return [UserComment(**m) async for m in self.db.iterate(
            """
            SELECT c.id,
                   u.username AS user,
                   c.comment,
                   c.modified_at,
                   p.name     AS project,
                   s.name     AS site,
                   m.id       AS memory
            FROM users u 
                     JOIN comments c ON c.user_id = u.id
                     JOIN memories m ON c.memory_id = m.id
                     JOIN sites s ON m.site_id = s.id
                     JOIN projects p ON s.project_id = p.id
            WHERE u.username = :user
            """,
            dict(user=user)
        )]
