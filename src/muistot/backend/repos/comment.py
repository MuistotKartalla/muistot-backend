from .base import *
from .exists import Status, check


class CommentRepo(BaseRepo):
    project: PID
    site: SID
    memory: MID

    _select = """
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

    _select_for_user = """
        SELECT c.id,
               u.username                                         AS user,
               c.comment,
               c.modified_at,
               IF(u2.id IS NOT NULL, NOT c.published, NULL)       AS waiting_approval,
               u.username = :user                                 AS own
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

    _select_for_admin = """
        SELECT c.id,
               u.username               AS user,
               c.comment,
               c.modified_at,
               IF(c.published, NULL, 1) AS waiting_approval,
               u.username = :user       AS own
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

    @staticmethod
    def construct_comment(m) -> Comment:
        return Comment(**m)

    def __init__(self, db: Database, project: PID, site: SID, memory: MID):
        super().__init__(db, project=project, site=site, memory=memory)

    @check.parents
    async def all(self, *, _status: Status) -> List[Comment]:
        values = dict(site=self.site, project=self.project, memory=self.memory)
        if _status.admin:
            sql = self._select_for_admin
            values.update(user=self.identity)
        elif self.authenticated:
            sql = self._select_for_user
            values.update(user=self.identity)
        else:
            sql = self._select
        return [
            self.construct_comment(m)
            async for m in self.db.iterate(sql, values=values)
            if m is not None
        ]

    @check.published_or_admin
    async def one(self, comment: CID, *, _status: Status) -> Comment:
        values = dict(
            site=self.site, project=self.project, memory=self.memory, comment=comment
        )
        if _status.admin:
            sql = self._select_for_admin
            values.update(user=self.identity)
        elif self.authenticated:
            sql = self._select_for_user
            values.update(user=self.identity)
        else:
            sql = self._select
        return self.construct_comment(
            await self.db.fetch_one(sql + " AND c.id = :comment", values=values)
        )

    @check.parents
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
            values=dict(
                memory=self.memory,
                user=self.identity,
                comment=model.comment,
                published=self.auto_publish,
            ),
        )

    @check.own
    async def modify(self, comment: CID, model: ModifiedComment) -> bool:
        await self.db.execute(
            """
            UPDATE comments 
            SET comment=:comment, published=DEFAULT
            WHERE id = :id
            """,
            values=dict(id=comment, comment=model.comment),
        )
        return True

    @check.own_or_admin
    async def delete(self, comment: CID):
        await self.db.execute(
            """
            DELETE FROM comments WHERE id = :id
            """,
            values=dict(id=comment),
        )

    @check.admin
    async def toggle_publish(self, comment: CID, publish: bool) -> bool:
        await self.db.execute(
            f'UPDATE comments r'
            f" SET r.published = {1 if publish else 0}"
            f' WHERE r.id = :id AND r.published = {0 if publish else 1}',
            values=dict(id=comment),
        )
        return await self.db.fetch_val("SELECT ROW_COUNT()")

    @check.exists
    async def report(self, comment: CID):
        await self.db.execute(
            """
            INSERT IGNORE INTO audit_comments (comment_id, user_id) 
            SELECT :cid, u.id
            FROM users u
            WHERE u.username = :user 
            """,
            values=dict(user=self.identity, cid=comment)
        )
