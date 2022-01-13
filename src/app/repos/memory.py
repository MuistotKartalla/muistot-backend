from .utils import *
from .comment import CommentRepo


class MemoryRepo(BaseRepo):
    project: PID
    site: SID
    _select = (
        """
        SELECT m.id,
               IF(m.deleted, '-', m.title)      AS title,
               IF(m.deleted, '-', m.story)      AS story,
               IF(m.deleted, '-', u.username)   AS user,
               IF(m.deleted, NULL, i.file_name) AS image,
               m.modified_at,
               COUNT(c.id)                      AS comments_count
        FROM memories m
                 JOIN sites s ON m.site_id = s.id
            AND s.name = :site
                 JOIN projects p ON s.project_id = p.id
            AND p.name = :project
                 JOIN users u ON m.user_id = u.id
                 JOIN images i ON m.image_id = i.id
                 LEFT JOIN comments c ON m.id = c.memory_id
                    AND c.published
        WHERE m.published {}
        GROUP BY m.id
        """
    )

    async def _exists(self, memory: MID) -> bool:
        m = await self.db.fetch_one(
            """
            SELECT ISNULL(s.id),
                   ISNULL(m.id),
                   s.published
            FROM projects p
                     LEFT JOIN sites s ON p.id = s.project_id
                AND s.name = :site
                     LEFT JOIN memories m ON s.id = m.site_id
                AND m.id = :memory
            WHERE p.name = :project AND p.published
            """,
            values=dict(memory=memory, site=self.site, project=self.project)
        )
        if m is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')
        elif m[0] == 1 and m[2] == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Site not found')
        return m[1] == 0

    def __init__(self, db: Database, project: PID, site: SID):
        super().__init__(db, project=project, site=site)

    @staticmethod
    def construct_memory(m) -> Memory:
        return Memory(**m)

    @check_parents
    async def all(self, include_comments: bool = False) -> List[Memory]:
        out = [self.construct_memory(m) async for m in self.db.iterate(
            self._select.format(''),
            values=dict(project=self.project, site=self.site)
        )]
        if include_comments:
            for m in out:
                m.comments = await CommentRepo(self.db, self.project, self.site, m.id).all()
        return out

    @check_exists
    async def one(self, memory: MID, include_comments: bool = False) -> Memory:
        out = self.construct_memory(await self.db.fetch_one(
            self._select.format("AND m.id = :memory"),
            values=dict(memory=memory, site=self.site, project=self.project)
        ))
        if include_comments:
            out.comments = await CommentRepo(self.db, self.project, self.site, out.id).all()
        return out

    @check_parents
    async def create(self, model: NewMemory) -> MID:
        if model.image is not None:
            image_id = await Files(self.db, self.user).handle(model.image)
        else:
            image_id = None
        return await self.db.fetch_val(
            """
            INSERT INTO memories (site_id, user_id, image_id, title, story)
            SELECT s.id, u.id, :image, :title, :story
            FROM sites s
                     JOIN users u ON u.username = :user
            WHERE s.name = :site
            RETURNING id
            """,
            values=dict(image=image_id, title=model.title, story=model.story, site=self.site)
        )

    @check_exists
    async def modify(self, memory: MID, model: ModifiedMemory) -> bool:
        if not await self.db.fetch_val(
                """
                SELECT u.username 
                FROM users u 
                WHERE u.id = (
                    SELECT c.user_id 
                    FROM comments c 
                    WHERE c.id = :comment 
                )
                """):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not yours')
        data = model.dict(exclude_unset=True)
        values = {}
        if 'image' in data:
            values['image_id'] = await Files(self.db, self.user).handle(model.image)
        else:
            values['image_id'] = None
        if len(values) > 0:
            return await self.db.fetch_val(
                f"""
                UPDATE memories
                SET {', '.join(f'{k}=:{k}' for k in data.keys)}
                WHERE id = :memory
                """,
                values=dict(**data, memory=memory)
            )

    @check_exists
    async def delete(self, memory: MID):
        await self.db.execute(
            """
            UPDATE memories SET deleted = 1 WHERE id = :id
            """,
            values=dict(id=memory)
        )

    @needs_admin
    @check_exists
    async def hard_delete(self, memory: MID):
        await self.db.execute(
            """
            DELETE FROM memories WHERE id = :id
            """,
            values=dict(id=memory)
        )

    @needs_admin
    @check_exists
    async def toggle_publish(self, memory: MID, published: bool):
        await self._set_published(published, id=memory)

    async def by_user(self, user: str) -> List[UserMemory]:
        return [UserMemory(**m) async for m in self.db.iterate(
            """
            SELECT m.id,
                   IF(m.deleted, '-', m.title)      AS title,
                   IF(m.deleted, '-', m.story)      AS story,
                   IF(m.deleted, '-', u.username)   AS user,
                   IF(m.deleted, NULL, i.file_name) AS image,
                   m.modified_at,
                   COUNT(c.id)                      AS comments_count,
                   p.name                           AS project,
                   s.name                           AS site
            FROM users u
                     JOIN memories m ON u.id = m.user_id
                     JOIN sites s ON m.site_id = s.id
                     JOIN projects p ON s.project_id = p.id
                     JOIN images i ON m.image_id = i.id
                     LEFT JOIN comments c ON m.id = c.memory_id
                        AND c.published
            WHERE u.username = :user
            GROUP BY m.id
            """,
            values=dict(user=user)
        )]
