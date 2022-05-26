from .base import *
from .comment import CommentRepo
from .exists import Status, check


class MemoryRepo(BaseRepo):
    project: PID
    site: SID

    _select = """
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
                 LEFT JOIN images i ON m.image_id = i.id
                 LEFT JOIN comments c ON m.id = c.memory_id
                    AND c.published
        WHERE m.published {}
        GROUP BY m.id
        """

    _select_for_user = """
        SELECT m.id,
               IF(m.deleted, '-', m.title)                      AS title,
               IF(m.deleted, '-', m.story)                      AS story,
               IF(m.deleted, '-', u.username)                   AS user,
               IF(m.deleted, NULL, i.file_name)                 AS image,
               m.modified_at,               
               COUNT(c.id)                                      AS comments_count,
               IF(u2.id IS NOT NULL, NOT m.published, NULL)     AS waiting_approval,
               u.username = :user                               AS own
        FROM memories m
                 JOIN sites s ON m.site_id = s.id
            AND s.name = :site
                 JOIN projects p ON s.project_id = p.id
            AND p.name = :project
                 JOIN users u ON m.user_id = u.id
                 LEFT JOIN images i ON m.image_id = i.id
                 LEFT JOIN comments c ON m.id = c.memory_id
            AND c.published
                 LEFT JOIN users u2 ON u2.id = m.user_id
                    AND u2.username = :user
        WHERE (m.published OR u2.id IS NOT NULL) {}
        GROUP BY m.id
        """

    _select_for_admin = """
        SELECT m.id,
               IF(m.deleted, '-', m.title)                      AS title,
               IF(m.deleted, '-', m.story)                      AS story,
               IF(m.deleted, '-', u.username)                   AS user,
               IF(m.deleted, NULL, i.file_name)                 AS image,
               m.modified_at,               
               COUNT(c.id)                                      AS comments_count,
               IF(m.published, NULL, 1)                         AS waiting_approval,
               u.username = :user                               AS own
        FROM memories m
                 JOIN sites s ON m.site_id = s.id
            AND s.name = :site
                 JOIN projects p ON s.project_id = p.id
            AND p.name = :project
                 JOIN users u ON m.user_id = u.id
                 LEFT JOIN images i ON m.image_id = i.id
                 LEFT JOIN comments c ON m.id = c.memory_id
            AND c.published
        WHERE TRUE {}
        GROUP BY m.id
        """

    def __init__(self, db: Database, project: PID, site: SID):
        super().__init__(db, project=project, site=site)

    @staticmethod
    def construct_memory(m) -> Memory:
        return Memory(**m)

    @check.parents
    async def all(self, include_comments: bool = False, *, _status: Status) -> List[Memory]:
        values = dict(site=self.site, project=self.project)
        if _status.admin:
            sql = self._select_for_admin
            values.update(user=self.identity)
        elif self.authenticated:
            sql = self._select_for_user
            values.update(user=self.identity)
        else:
            sql = self._select
        out = [
            self.construct_memory(m)
            async for m in self.db.iterate(sql.format(""), values=values)
            if m is not None
        ]
        if include_comments:
            for m in out:
                m.comments = await CommentRepo(
                    self.db, self.project, self.site, m.id
                ).all()
        return out

    @check.published_or_admin
    async def one(self, memory: MID, include_comments: bool = False, *, _status: Status) -> Memory:
        values = dict(memory=memory, site=self.site, project=self.project)
        if _status.admin:
            sql = self._select_for_admin
            values.update(user=self.identity)
        elif self.authenticated:
            sql = self._select_for_user
            values.update(user=self.identity)
        else:
            sql = self._select

        out = self.construct_memory(
            await self.db.fetch_one(sql.format("AND m.id = :memory"), values=values)
        )

        if include_comments:
            out.comments = await CommentRepo(self.db, self.project, self.site, out.id).from_repo(self).all()

        return out

    @check.parents
    async def create(self, model: NewMemory) -> MID:
        if model.image is not None:
            image_id = await self.files.handle(model.image)
        else:
            image_id = None
        return await self.db.fetch_val(
            """
            INSERT INTO memories (site_id, user_id, image_id, title, story, published)
            SELECT s.id, u.id, :image, :title, :story, :published
            FROM sites s
                     JOIN users u ON u.username = :user
            WHERE s.name = :site
            RETURNING id
            """,
            values=dict(
                image=image_id,
                title=model.title,
                story=model.story,
                site=self.site,
                user=self.identity,
                published=self.auto_publish,
            ),
        )

    @check.own
    async def modify(self, memory: MID, model: ModifiedMemory) -> bool:
        data = model.dict(exclude_unset=True)
        if "image" in data:
            data.pop("image")
            data["image_id"] = await self.files.handle(model.image)
        if len(data) > 0:
            await self.db.execute(
                f"""
                UPDATE memories
                SET {', '.join(f'{k}=:{k}' for k in data.keys())}
                WHERE id = :memory
                """,
                values=dict(**data, memory=memory),
            )
            return True
        return False

    @check.own_or_admin
    async def delete(self, memory: MID):
        await self.db.execute(
            """
            DELETE FROM memories WHERE id = :id
            """,
            values=dict(id=memory),
        )

    @check.admin
    async def toggle_publish(self, memory: MID, publish: bool) -> bool:
        await self.db.execute(
            f'UPDATE memories r'
            f" SET r.published = {1 if publish else 0}"
            f' WHERE r.id = :id',
            values=dict(id=memory),
        )
        return await self.db.fetch_val("SELECT ROW_COUNT()")

    @check.exists
    async def report(self, memory: MID):
        await self.db.execute(
            """
            INSERT IGNORE INTO audit_memories (memory_id, user_id) 
            SELECT :mid, u.id
            FROM users u
            WHERE u.username = :user 
            """,
            values=dict(user=self.identity, mid=memory)
        )
