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
                 JOIN users u ON c.user_id = u.id
                 JOIN memories m ON c.memory_id = m.id
            AND m.id = :memory
                 JOIN sites s ON m.site_id = s.id
            AND s.name = :site
                 JOIN projects p ON s.project_id = p.id
            AND p.name = :project
        WHERE c.published
        """
    )

    async def _exists(self, comment: CID) -> bool:
        m = await self.db.fetch_one(
            """
            SELECT ISNULL(s.id),
                   ISNULL(m.id),
                   ISNULL(c.id),
                   s.published,
                   m.published
            FROM projects p
                     LEFT JOIN sites s ON p.id = s.project_id
                AND s.name = :site
                     LEFT JOIN memories m ON s.id = m.site_id
                AND m.id = :memory
                     LEFT JOIN comments c ON m.id = c.memory_id
                AND c.id = :comment
            WHERE p.name = :project
              AND p.published
            """,
            values=dict(comment=comment, memory=self.memory, site=self.site, project=self.project)
        )
        if m is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')
        elif m[0] == 1 and m[3] == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Site not found')
        elif m[1] == 1 and m[4] == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Memory not found')
        return m[2] == 0

    @staticmethod
    def construct_comment(m) -> Comment:
        return Comment(**m)

    def __init__(self, db: Database, project: PID, site: SID, memory: MID):
        super().__init__(db, project=project, site=site, memory=memory)

    @check_parents
    async def all(self) -> List[Comment]:
        return [self.construct_comment(m) async for m in self.db.iterate(
            self._select,
            values=dict(project=self.project, site=self.site, memory=self.memory)
        )]

    @check_exists
    async def one(self, comment: CID) -> Comment:
        return self.construct_comment(await self.db.fetch_one(
            self._select + ' AND c.id = :comment',
            values=dict(project=self.project, site=self.site, memory=self.memory, comment=comment)
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
            values=dict(memory=self.memory, user=self.user.identity, comment=model.comment)
        )

    @check_exists
    async def modify(self, comment: CID, model: ModifiedComment) -> bool:
        if not self.user.is_admin_in(self.project):
            comment_user = await self.db.fetch_val(
                "SELECT u.username FROM users u JOIN comments c ON u.id = c.user_id WHERE c.id = :comment",
                values=dict(comment=comment)
            )
            if comment_user != self.user.identity and not self.user.is_admin_in(self.project):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Not author')
        return await self.db.fetch_val(
            """
            UPDATE comments 
            SET comment=:comment 
            WHERE id = :id
            """,
            values=dict(id=comment, comment=model.comment)
        ) == 1

    @check_exists
    async def delete(self, comment: CID):
        await self.db.fetch_val(
            """
            DELETE c FROM comments c
            JOIN users u ON c.user_id = u.id
                AND u.id = :user
            WHERE c.id = :cid 
            """
        )

    @needs_admin
    @check_exists
    async def toggle_publish(self, comment: CID, published: bool):
        await self._set_published(published, id=comment)

    @check_parents
    async def by_user(self, user: str) -> List[UserComment]:
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
