from .base import *
from .memory import MemoryRepo


class SiteRepo(BaseRepo):
    project: PID

    __select = (
        """
        SELECT
            s.name                                      AS id,
            COALESCE(si.name, def_si.name, s.name)      AS name,
            Y(s.location)                               AS lat,
            X(s.location)                               AS lon,
            i.file_name                                 AS image,
            COUNT(m.id)                                 AS memories_count,
            IFNULL(l.lang, def_l.lang)                  AS lang,
            IFNULL(si.abstract, def_si.abstract)        AS abstract,
            IFNULL(si.description, def_si.description)  AS description,
            IF(s.published, NULL, 1)                    AS waiting_approval
            %s
        FROM sites s
            JOIN projects p ON p.id = s.project_id
                AND p.name = :project
            LEFT JOIN site_information si 
                JOIN languages l ON si.lang_id = l.id
                    AND l.lang = :lang
                ON s.id = si.site_id 
            LEFT JOIN site_information def_si 
                JOIN languages def_l ON def_si.lang_id = def_l.id
                ON s.id = def_si.site_id
                    AND def_si.lang_id = p.default_language_id 
            LEFT JOIN memories m ON s.id = m.site_id
                AND m.published
            LEFT JOIN images i ON i.id = s.image_id
            LEFT JOIN users um ON um.id = s.modifier_id
                AND um.username = :user
        {}
        GROUP BY s.id
        %s
        """
    )

    _select = (__select % ('', ''))
    _select_dist = __select % (
        ",\nST_DISTANCE_SPHERE(s.location, POINT(:lon, :lat)) AS distance",
        " ORDER BY distance LIMIT {:d}"
    )

    async def _exists(self, site: SID) -> Status:
        if self.has_identity:
            m = await self.db.fetch_one(
                """
                SELECT p.published,
                       s.published,
                       ISNULL(pa.user_id)
                FROM projects p
                        LEFT JOIN sites s ON p.id = s.project_id
                    AND s.name = :site
                        LEFT JOIN project_admins pa
                            JOIN users u2 ON pa.user_id = u2.id
                                AND u2.username = :user
                         ON p.id = pa.project_id
                WHERE p.name = :project
                """,
                values=dict(site=site, project=self.project, user=self.identity)
            )
        else:
            m = await self.db.fetch_one(
                """
                SELECT p.published,
                       s.published
                FROM projects p
                         LEFT JOIN sites s ON p.id = s.project_id
                    AND s.name = :site
                WHERE p.name = :project
                """,
                values=dict(site=site, project=self.project)
            )
        if m is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')

        s = Status.resolve(m[1])

        if self.has_identity and s != Status.DOES_NOT_EXIST:
            if m[2] == 0:
                return Status.ADMIN

        if m[0] == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')

        return s

    def __init__(self, db: Database, project: PID):
        super().__init__(db, project=project)

    async def _handle_info(self, site: SID, model: SiteInfo) -> bool:
        if model is None:
            return False
        else:
            return await self.db.fetch_val(
                """
                REPLACE INTO site_information (site_id, lang_id, name, abstract, description, modifier_id)
                SELECT s.id,
                       l.id,
                       :name,
                       :abstract,
                       :description,
                       u.id
                FROM languages l
                    JOIN sites s ON s.name = :site
                    LEFT JOIN users u ON u.username = :user
                WHERE l.lang = :lang
                RETURNING lang_id
                """,
                values=dict(
                    site=site,
                    **model.dict(),
                    user=self.identity
                )
            )

    @staticmethod
    def construct_site(m) -> Site:
        return Site(location=Point(**m), info=SiteInfo(**m), **m)

    @check_parents
    async def all(
            self,
            n: Optional[int] = None,
            lat: Optional[float] = None,
            lon: Optional[float] = None,
            *,
            _status: Status
    ) -> List[Site]:
        values = dict(lang=self.lang, project=self.project, user=self.identity)
        if _status == Status.ADMIN:
            where = 'WHERE TRUE'
        elif self.has_identity:
            where = 'WHERE (s.published OR um.username = :user)'
        else:
            where = 'WHERE s.published'
        if n is not None and lat is not None and lon is not None:
            if n < 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='negative n')
            values.update(lon=lon, lat=lat)
            out = [self.construct_site(m) async for m in self.db.iterate(
                self._select_dist.format(where, n),
                values=values
            ) if m is not None]
        else:
            out = [self.construct_site(m) async for m in self.db.iterate(
                self._select.format(where),
                values=values
            ) if m is not None]
        return out

    @check_published_or_admin
    async def one(self, site: SID, include_memories: bool = False, *, _status: Status) -> Site:
        values = dict(lang=self.lang, project=self.project, site=site, user=self.identity)
        if _status == Status.ADMIN:
            where = 'WHERE TRUE'
        elif self.has_identity:
            where = (
                'WHERE (s.published OR um.username = :user)'
            )
        else:
            where = 'WHERE s.published'
        out = self.construct_site(await self.db.fetch_one(
            self._select.format(where + " AND s.name = :site"),
            values=values
        ))
        if include_memories:
            out.memories = await MemoryRepo(self.db, self.project, out.id)._configure(self).all(include_comments=False)
        return out

    @check_not_exists
    async def create(self, model: NewSite) -> SID:
        check_id(model.id)
        check_language(model.info.lang)
        image_id = await self.files.handle(model.image)
        ret = await self.db.fetch_one(
            """
            INSERT INTO sites (project_id, name, image_id, published, location, modifier_id)
            SELECT p.id,
                   :name,
                   :image,
                   :published,
                   POINT(:lon, :lat),
                   u.id
            FROM projects p
                LEFT JOIN users u ON u.username = :user
            WHERE p.name = :project
            RETURNING id, name
            """,
            values=dict(
                name=model.id,
                image=image_id,
                published=self.auto_publish,
                lon=model.location.lon,
                lat=model.location.lat,
                project=self.project,
                user=self.identity
            )
        )
        _id, name = ret
        await self._handle_info(name, model.info)
        return name

    @check_admin
    async def modify(self, site: SID, model: ModifiedSite) -> bool:
        data = model.dict(exclude_unset=True)
        if 'image' in data:
            image_id = await self.files.handle(model.image)
        else:
            image_id = None
        if 'location' in data:
            modified = await self.db.fetch_val(
                f"""
                UPDATE sites 
                SET location=POINT(:lon, :lat), {'' if image_id is None else 'image_id=:image'},
                    modifier_id = (SELECT id FROM users WHERE username = :user)
                WHERE name = :site
                """,
                values=dict(
                    site=site,
                    lon=model.location.lon,
                    lat=model.location.lat,
                    **(dict() if image_id is None else dict(image=image_id)),
                    user=self.identity
                )
            ) == 1
        elif image_id is not None:
            modified = await self.db.fetch_val(
                f"""
                UPDATE sites s
                    LEFT JOIN users u ON u.username = :user
                SET s.image_id = :image, s.modifier_id = u.id
                WHERE s.name = :site
                """,
                values=dict(
                    site=site,
                    image=image_id,
                    user=self.identity
                )
            ) == 1
        else:
            modified = True
        if 'info' in data:
            modified = self._handle_info(site, model.info)
        return modified

    @check_admin
    async def delete(self, site: SID):
        await self.db.execute(
            """
            DELETE FROM sites WHERE name = :id
            """,
            values=dict(id=site)
        )

    @check_admin
    async def toggle_publish(self, site: SID, published: bool):
        await self._set_published(published, name=site)

    @check_admin
    async def localize(self, site: SID, localized_data: SiteInfo):
        await self._handle_info(site, localized_data)
