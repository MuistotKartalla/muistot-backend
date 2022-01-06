from .repo_utils import *


#        ___           ___           ___           ___           ___
#       /\  \         /\  \         /\  \         /\  \         /\  \
#      /::\  \        \:\  \       /::\  \       /::\  \        \:\  \
#     /:/\ \  \        \:\  \     /:/\:\  \     /:/\:\  \        \:\  \
#    _\:\~\ \  \       /::\  \   /::\~\:\  \   /::\~\:\  \       /::\  \
#   /\ \:\ \ \__\     /:/\:\__\ /:/\:\ \:\__\ /:/\:\ \:\__\     /:/\:\__\
#   \:\ \:\ \/__/    /:/  \/__/ \/__\:\/:/  / \/_|::\/:/  /    /:/  \/__/
#    \:\ \:\__\     /:/  /           \::/  /     |:|::/  /    /:/  /
#     \:\/:/  /     \/__/            /:/  /      |:|\/__/     \/__/
#      \::/  /                      /:/  /       |:|  |
#       \/__/                       \/__/         \|__|

class ProjectRepo(BaseRepo):
    _select = (
        """
        SELECT
            p.id AS project_id,
            p.name AS id,
            i.file_name AS image,
            l.lang,
            IFNULL(pi.name, p.name) AS name,
            pi.abstract,
            pi.description,
            p.starts,
            p.ends,
            pc.has_research_permit,
            IF(pc.can_contact, pc.contact_email, NULL) AS contact_email
        FROM projects p
            JOIN project_information pi ON p.id = pi.project_id
            JOIN languages l ON pi.lang_id = l.id
                AND l.lang = :lang
            LEFT JOIN images i ON p.image_id = i.id
            LEFT JOIN project_contact pc ON p.id = pc.project_id
        WHERE IFNULL(p.starts > CURDATE(), TRUE) AND p.published
        """
    )

    async def get_admins(self, project_id: int):
        out = [admin[0] for admin in await self.db.fetch_all(
            """
            SELECT
                u.username
            FROM project_admins pa
                JOIN users u ON pa.user_id = u.id
            WHERE project_id = :pid
            """,
            values=dict(pid=project_id)
        )]
        return out if len(out) > 0 else None

    async def _exists(self, project: PID) -> bool:
        return await self.db.fetch_val(
            'SELECT EXISTS(SELECT 1 FROM projects WHERE name = :project)',
            values=dict(project=project)
        ) == 1

    @check_lang
    async def construct_project(self, m):
        pi = ProjectInfo(**m)
        if not m[8] is None:
            pc = ProjectContact(**m)
        else:
            pc = None
        return Project(
            **m,
            info=pi,
            contact=pc,
            admins=await self.get_admins(m[0])
        )

    async def all(self) -> List[Project]:
        return [await self.construct_project(m) for m in await self.db.fetch_all(
            self._select,
            values=dict(lang=self.lang)
        ) if m is not None]

    @check_exists
    async def one(self, project: PID) -> Project:
        return await self.construct_project(await self.db.fetch_one(
            self._select + " AND p.name = :project",
            values=dict(lang=self.lang, project=project)
        ))

    @not_implemented
    @check_not_exists
    @needs_admin
    async def create(self, model: Project) -> PID:
        # TODO:
        pass

    @not_implemented
    @check_exists
    @needs_admin
    async def modify(self, project: PID, model: ModifiedProject) -> bool:
        # TODO:
        pass

    @needs_admin
    @set_published(False)
    async def delete(self, project: PID):
        return "name = :project", dict(project=project)

    @needs_admin
    @set_published(True)
    async def publish(self, project: PID):
        return "name = :project", dict(project=project)


class SiteRepo(BaseRepo):
    project: PID

    _fields = (
        """
        SELECT
            s.name AS id,
            IFNULL(si.name, s.name) AS name,
            X(s.location) AS lat,
            Y(s.location) AS lon,
            i.file_name AS image,
            COUNT(m.id) AS memories_count,
            l.lang,
            si.abstract,
            si.description
        """
    )
    _end = (
        """
        FROM sites s
            JOIN projects p ON p.id = s.project_id
                AND p.name = :project
            JOIN site_information si ON s.id = si.site_id
            JOIN languages l ON si.lang_id = l.id
                AND l.lang = :lang
            LEFT JOIN memories m ON s.id = m.site_id
            LEFT JOIN images i ON i.id = s.image_id
        WHERE s.published {}
        GROUP BY s.id
        """
    )
    _select = (
        f"""
        {_fields}
        {_end}
        """
    )

    async def _exists(self, site: SID) -> bool:
        m = await self.db.fetch_one(
            """
            SELECT 
                ISNULL(s.id) 
            FROM projects p 
                LEFT JOIN sites s ON p.id = s.project_id
                    AND s.name = :site
            WHERE p.name = :project AND p.published
            """,
            values=dict(site=site, project=self.project)
        )
        if m is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')
        return m[0] == 0

    def __init__(self, db: Database, project: PID):
        super().__init__(db, project=project)

    @check_lang
    async def construct_site(self, m):
        return Site(location=Point(**m), info=SiteInfo(**m), **m)

    async def all(
            self,
            n: Optional[int],
            lat: Optional[float],
            lon: Optional[float],
            include_memories: bool = False
    ) -> List[Site]:
        if n is not None and lat is not None and lon is not None:
            if n < 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='negative n')
            return [await self.construct_site(m) for m in await self.db.fetch_all(
                self._fields
                + ",\nST_DISTANCE_SPHERE(s.location, POINT(:lon, :lat)) AS distance"
                + self._end.format('')
                + " ORDER BY distance LIMIT {:d}".format(n),
                values=dict(lang=self.lang, lon=lon, lat=lat, project=self.project)
            )]
        else:
            return [await self.construct_site(m) for m in await self.db.fetch_all(
                self._select.format(''),
                values=dict(lang=self.lang, project=self.project)
            )]

    @check_exists
    async def one(self, site: SID, include_memories: bool = False) -> Site:
        return await self.construct_site(await self.db.fetch_one(
            self._select.format(" AND s.name = :site"),
            values=dict(lang=self.lang, project=self.project, site=site)
        ))

    @check_not_exists
    async def create(self, model: NewSite) -> SID:
        check_id(model.id)
        check_language(model.info.lang)
        image_id = await Files(self.db, self.user).handle(model.image)
        ret = await self.db.fetch_one(
            """
            INSERT INTO sites (project_id, name, image_id, published, location) 
            SELECT 
                p.id,
                :name,
                :image,
                :published,
                POINT(:lon, :lat)
            FROM projects p
                WHERE p.name = :project
            RETURNING id, name
            """,
            values=dict(
                name=model.id,
                image=image_id,
                published=self.auto_publish,
                lon=model.location.lon,
                lat=model.location.lat,
                project=self.project
            )
        )
        if ret[1] is None:  # pragma: no cover
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Failed to save site'
            )
        await self.db.fetch_val(
            """
            INSERT INTO site_information (site_id, lang_id, name, abstract, description) 
            SELECT
                :site,
                l.id,
                :name,
                :abstract,
                :description
            FROM languages l
                WHERE l.lang = :lang
            """,
            values=dict(
                site=ret[0],
                **model.info.dict()
            )
        )
        return ret[1]

    @not_implemented
    @check_exists
    @needs_admin
    async def modify(self, site: SID, model: ModifiedSite) -> bool:
        # TODO:
        pass

    @needs_admin
    @set_published(False)
    async def delete(self, site: SID):
        return "id = :sid", dict(sid=site)

    @needs_admin
    @set_published(True)
    async def publish(self, site: SID):
        return "id = :sid", dict(sid=site)

    @not_implemented
    async def by_user(self, user: str) -> List[Site]:
        # TODO:
        pass


class MemoryRepo(BaseRepo):
    project: PID
    site: SID

    async def _exists(self, memory: MID) -> bool:
        m = await self.db.fetch_one(
            """
            SELECT
                ISNULL(s.id),
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

    @not_implemented
    async def all(self) -> List[Memory]:
        # TODO:
        pass

    @not_implemented
    @check_exists
    async def one(self, memory: MID) -> Memory:
        # TODO:
        pass

    @not_implemented
    @check_not_exists
    async def create(self, model: NewMemory) -> MID:
        # TODO:
        pass

    @not_implemented
    @check_exists
    async def modify(self, memory: MID, model: ModifiedMemory) -> bool:
        # TODO:
        pass

    @not_implemented
    async def delete(self, memory: MID):
        # TODO:
        pass

    @not_implemented
    async def publish(self, memory: MID):
        # TODO:
        pass

    @not_implemented
    async def by_user(self, user: str) -> List[Memory]:
        # TODO:
        pass


class CommentRepo(BaseRepo):
    project: PID
    site: SID
    memory: MID

    _select = (
        """
        SELECT
            c.id,
            u.username AS user,
            c.comment
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
            SELECT
                ISNULL(s.id),
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
            WHERE p.name = :project AND p.published
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
    async def construct_comment(m) -> Comment:
        return Comment.construct(Comment.__fields_set__, **m)

    def __init__(self, db: Database, project: PID, site: SID, memory: MID):
        super().__init__(db, project=project, site=site, memory=memory)

    async def all(self) -> List[Comment]:
        return [await self.construct_comment(m) for m in await self.db.fetch_all(
            self._select,
            values=dict(project=self.project, site=self.site, memory=self.memory)
        )]

    @check_exists
    async def one(self, comment: CID) -> Comment:
        return await self.construct_comment(await self.db.fetch_one(
            self._select + ' AND c.id = :comment',
            values=dict(project=self.project, site=self.site, memory=self.memory, comment=comment)
        ))

    async def create(self, model: NewComment) -> CID:
        await MemoryRepo(self.db, self.project, self.site)._check_exists(self.memory)
        return await self.db.fetch_val(
            """
            INSERT INTO comments (memory_id, user_id, comment, published) 
            SELECT
                m.id,
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
    async def delete(self, comment: CID) -> bool:
        return await self.db.fetch_val(
            """
            DELETE c FROM comments c
            JOIN users u ON c.user_id = u.id
                AND u.id = :user
            WHERE c.id = :cid 
            """
        ) == 1

    @needs_admin
    @set_published(True)
    async def publish(self, comment: CID):
        return "id = :cid", dict(cid=comment)

    @not_implemented
    async def by_user(self, user: str) -> List[Comment]:
        # TODO:
        pass


__all__ = [
    'ProjectRepo',
    'SiteRepo',
    'MemoryRepo',
    'CommentRepo'
]
