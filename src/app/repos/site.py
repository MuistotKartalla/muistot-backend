from .utils import *
from .memory import MemoryRepo


class SiteRepo(BaseRepo):
    project: PID
    _fields = (
        """
        SELECT
            s.name AS id,
            COALESCE(si.name, def_si.name, s.name) AS name,
            Y(s.location) AS lat,
            X(s.location) AS lon,
            i.file_name AS image,
            COUNT(m.id) AS memories_count,
            IFNULL(l.lang, def_l.lang) AS lang,
            IFNULL(si.abstract, def_si.abstract) AS abstract,
            IFNULL(si.description, def_si.description) AS description
        """
    )
    _end = (
        """
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

        WHERE s.published
            {}
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
            SELECT ISNULL(s.id)
            FROM projects p
                     LEFT JOIN sites s ON p.id = s.project_id
                AND s.name = :site
            WHERE p.name = :project
              AND p.published
            """,
            values=dict(site=site, project=self.project)
        )
        if m is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')
        return m[0] == 0

    def __init__(self, db: Database, project: PID):
        super().__init__(db, project=project)

    async def _handle_info(self, site: SID, model: SiteInfo) -> bool:
        if model is None:
            return False
        else:
            return await self.db.fetch_val(
                """
                REPLACE INTO site_information (site_id, lang_id, name, abstract, description)
                SELECT s.id,
                       l.id,
                       :name,
                       :abstract,
                       :description
                FROM languages l
                    JOIN sites s ON s.name = :site
                WHERE l.lang = :lang
                RETURNING l.id
                """,
                values=dict(
                    site=site,
                    **model.dict()
                )
            )

    @staticmethod
    def construct_site(m) -> Site:
        return Site(location=Point(**m), info=SiteInfo(**m), **m)

    @check_parents
    async def all(
            self,
            n: Optional[int],
            lat: Optional[float],
            lon: Optional[float]
    ) -> List[Site]:
        if n is not None and lat is not None and lon is not None:
            if n < 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='negative n')
            out = [self.construct_site(m) async for m in self.db.iterate(
                self._fields
                + ",\nST_DISTANCE_SPHERE(s.location, POINT(:lon, :lat)) AS distance"
                + self._end.format('')
                + " ORDER BY distance LIMIT {:d}".format(n),
                values=dict(lang=self.lang, lon=lon, lat=lat, project=self.project)
            )]
        else:
            out = [self.construct_site(m) async for m in self.db.iterate(
                self._select.format(''),
                values=dict(lang=self.lang, project=self.project)
            )]
        return out

    @check_exists
    async def one(self, site: SID, include_memories: bool = False) -> Site:
        out = self.construct_site(await self.db.fetch_one(
            self._select.format(" AND s.name = :site"),
            values=dict(lang=self.lang, project=self.project, site=site)
        ))
        if include_memories:
            out.memories = await MemoryRepo(self.db, self.project, out.id).all(include_comments=False)
        return out

    @check_not_exists
    async def create(self, model: NewSite) -> SID:
        check_id(model.id)
        check_language(model.info.lang)
        image_id = await Files(self.db, self.user).handle(model.image)
        ret = await self.db.fetch_one(
            """
            INSERT INTO sites (project_id, name, image_id, published, location)
            SELECT p.id,
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
        _id, name = ret
        if name is None:  # pragma: no cover
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Failed to save site'
            )
        await self._handle_info(name, model.info)
        return _id

    @needs_admin
    @check_exists
    async def modify(self, site: SID, model: ModifiedSite) -> bool:
        data = model.dict(exclude_unset=True)
        if 'image' in data:
            image_id = await Files(self.db, self.user).handle(model.image)
        else:
            image_id = None
        if 'location' in data:
            modified = await self.db.fetch_val(
                f"""
                UPDATE sites 
                SET location=POINT(:lon, :lat), {'' if image_id is None else 'image_id=:image'}
                WHERE name = :site
                """,
                values=dict(
                    site=site,
                    lon=model.location.lon,
                    lat=model.location.lat,
                    **(dict() if image_id is None else dict(image=image_id))
                )
            ) == 1
        elif image_id is not None:
            modified = await self.db.fetch_val(
                f"""
                UPDATE sites 
                SET image_id=:image
                WHERE name = :site
                """,
                values=dict(
                    site=site,
                    image=image_id
                )
            ) == 1
        else:
            modified = True
        if 'info' in data:
            modified = self._handle_info(site, model.info)
        return modified

    @needs_admin
    @check_exists
    async def delete(self, site: SID):
        await self.db.execute(
            """
            DELETE FROM sites WHERE name = :id
            """,
            values=dict(id=site)
        )

    @needs_admin
    @check_exists
    async def toggle_publish(self, site: SID, published: bool):
        await self._set_published(published, name=site)

    @needs_admin
    @check_exists
    async def localize(self, site: SID, localized_data: SiteInfo):
        await self._handle_info(site, localized_data)
