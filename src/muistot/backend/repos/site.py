import random

from .base import *
from .exists import Status, check
from .memory import MemoryRepo


class SiteRepo(BaseRepo):
    project: PID

    __select = """
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
            IF(s.published, NULL, 1)                    AS waiting_approval,
            IF(uc.id IS NOT NULL, TRUE, NULL)           AS own
            %s
        FROM sites s
            JOIN projects p ON p.id = s.project_id
                AND p.name = :project
            LEFT JOIN site_information si 
                JOIN languages l ON si.lang_id = l.id
                    AND l.lang = :lang
                ON s.id = si.site_id 
                
            JOIN site_information def_si ON s.id = def_si.site_id
                    AND def_si.lang_id = p.default_language_id 
            JOIN languages def_l ON def_si.lang_id = def_l.id
                
            LEFT JOIN memories m ON s.id = m.site_id
                AND m.published
            LEFT JOIN images i ON i.id = s.image_id
            LEFT JOIN users um ON um.id = s.modifier_id
                AND um.username = :user
            LEFT JOIN users uc ON uc.id = s.creator_id
                AND uc.username = :user
        {}
        GROUP BY s.id
        %s
        """

    _select = __select % ("", "")
    _select_dist = __select % (
        ",\nST_DISTANCE_SPHERE(s.location, POINT(:lon, :lat)) AS distance",
        " ORDER BY distance LIMIT {:d}",
    )

    def __init__(self, db: Database, project: PID):
        super().__init__(db, project=project)

    def _check_pap(self, _status: Status):
        if _status.pap and not self.admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin posting only")

    async def _handle_info(self, site: SID, model: SiteInfo) -> bool:
        if model is None:
            return False
        else:
            await self.db.fetch_val(
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
                """,
                values=dict(site=site, **model.dict(), user=self.identity),
            )
            return True

    async def _handle_image(self, site: SID, data) -> bool:
        if "image" in data:
            image_data = data["image"]
            if image_data is None:
                await self.db.execute(
                    f"""
                    UPDATE sites s
                        LEFT JOIN users u ON u.username = :user
                    SET s.image_id = NULL, s.modifier_id = u.id
                    WHERE s.name = :site
                    """,
                    values=dict(site=site, user=self.identity),
                )
            else:
                image_id = await self.files.handle(image_data)
                await self.db.execute(
                    f"""
                    UPDATE sites s
                        LEFT JOIN users u ON u.username = :user
                    SET s.image_id = :image, s.modifier_id = u.id
                    WHERE s.name = :site
                    """,
                    values=dict(site=site, image=image_id, user=self.identity),
                )
            return True
        else:
            return False

    async def _handle_location(self, site: SID, model: Point):
        if model is not None:
            await self.db.execute(
                f"""
                UPDATE sites 
                SET location=POINT(:lon, :lat),
                    modifier_id = (SELECT id FROM users WHERE username = :user)
                WHERE name = :site
                """,
                values=dict(
                    site=site,
                    lon=model.lon,
                    lat=model.lat,
                    user=self.identity,
                ),
            )
            return True
        else:
            return False

    async def _get_project_default_lang(self):
        project_default = await self.db.fetch_val(
            """
            SELECT l.lang
            FROM projects p 
                JOIN languages l on p.default_language_id = l.id
            WHERE p.name = :project
            """,
            values=dict(project=self.project)
        )
        return project_default

    async def _get_random_image(self, site: SID):
        image: Optional[bytes] = self._cache.get(site, prefix="sites")
        if image is None:
            images = list(map(lambda m: m[0], await self.db.fetch_all(
                """
                SELECT i.file_name FROM  sites s
                    JOIN memories m on s.id = m.site_id
                        AND m.published
                    JOIN images i on m.image_id = i.id
                WHERE s.name = :site
                ORDER BY RAND()
                LIMIT 1
                """,
                values=dict(site=site)
            )))
            image: str = random.choice(images) if len(images) > 0 else None
            self._cache.set(site, image or "", prefix="sites", ttl=60 * 5)
        elif len(image) == 0:
            image = None
        else:
            image: str = image.decode("utf-8")
        return image

    async def construct_site(self, m) -> Site:
        if m.get("memories_count", 0) > 0 and m.get("image", None) is None:
            m = dict(**m)
            m["image"] = await self._get_random_image(m["id"])
        return Site(location=Point(**m), info=SiteInfo(**m), **m)

    @check.parents
    async def all(
            self,
            n: Optional[int] = None,
            lat: Optional[float] = None,
            lon: Optional[float] = None,
            *,
            _status: Status,
    ) -> List[Site]:
        values = dict(lang=self.lang, project=self.project, user=self.identity)
        if _status.admin:
            where = "WHERE TRUE"
        elif self.authenticated:
            where = "WHERE (s.published OR um.username = :user)"
        else:
            where = "WHERE s.published"
        if n is not None and lat is not None and lon is not None:
            if n < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="negative n"
                )
            values.update(lon=lon, lat=lat)
            out = [
                await self.construct_site(m)
                async for m in self.db.iterate(
                    self._select_dist.format(where, n), values=values
                )
                if m is not None
            ]
        else:
            out = [
                await self.construct_site(m)
                async for m in self.db.iterate(
                    self._select.format(where), values=values
                )
                if m is not None
            ]
        return out

    @check.published_or_admin
    async def one(self, site: SID, include_memories: bool = False, *, _status: Status) -> Site:
        values = dict(
            lang=self.lang, project=self.project, site=site, user=self.identity
        )
        if _status.admin:
            where = "WHERE TRUE"
        elif self.authenticated:
            where = "WHERE (s.published OR um.username = :user)"
        else:
            where = "WHERE s.published"

        m = await self.db.fetch_one(self._select.format(where + " AND s.name = :site"), values=values)
        if m is None:
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail='Site missing default localization'
            )
        out = await self.construct_site(m)
        if include_memories:
            out.memories = await MemoryRepo(self.db, self.project, out.id).from_repo(self).all(include_comments=False)
        return out

    @check.not_exists
    async def create(self, model: NewSite, _status: Status) -> SID:
        self._check_pap(_status)
        check_language(model.info.lang)
        image_id = await self.files.handle(model.image)
        ret = await self.db.fetch_one(
            """
            INSERT INTO sites (project_id, name, image_id, published, location, modifier_id, creator_id)
            SELECT p.id,
                   :name,
                   :image,
                   :published,
                   POINT(:lon, :lat),
                   u.id,
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
                user=self.identity,
            ),
        )
        _id, name = ret
        await self._handle_info(name, model.info)
        default_lang = await self._get_project_default_lang()
        if default_lang != model.info.lang:
            info = model.info
            info.lang = default_lang
            info.description = None
            info.abstract = None
            await self._handle_info(name, info)
        return name

    @check.own_or_admin
    async def modify(self, site: SID, model: ModifiedSite, _status: Status) -> bool:
        self._check_pap(_status)
        data = model.dict(exclude_unset=True)
        modified = False
        modified |= await self._handle_image(site, data)
        if "location" in data:
            modified |= await self._handle_location(site, model.location)
        if "info" in data:
            modified |= await self._handle_info(site, model.info)
        return bool(modified)

    @check.own_or_admin
    async def delete(self, site: SID):
        await self.db.execute(
            """
            DELETE FROM sites WHERE name = :id
            """,
            values=dict(id=site),
        )

    @check.admin
    async def toggle_publish(self, site: SID, published: bool):
        await self._set_published(published, name=site)

    @check.exists
    async def localize(self, site: SID, localized_data: SiteInfo, _status: Status):
        self._check_pap(_status)
        await self._handle_info(site, localized_data)
