import random
from typing import List, Optional

from starlette.exceptions import HTTPException
from starlette.status import HTTP_406_NOT_ACCEPTABLE, HTTP_403_FORBIDDEN

from .base import BaseRepo, append_identifier
from .memory import MemoryRepo
from .status import SiteStatus, Status, require_status
from ..models import PID, SID, Site, SiteInfo, NewSite, ModifiedSite, Point


class SiteRepo(BaseRepo, SiteStatus):
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
            IF(uc.username = :user, TRUE, NULL)         AS own,
            uc.username                                 AS creator,
            um.username                                 AS modifier
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
            LEFT JOIN users um ON um.id = si.modifier_id
            LEFT JOIN users uc ON uc.id = s.creator_id
        {}
        GROUP BY s.id
        %s
        """

    _select = __select % ("", "")
    _select_dist = __select % (
        ",\nST_DISTANCE_SPHERE(s.location, POINT(:lon, :lat)) AS distance",
        " ORDER BY distance LIMIT {:d}",
    )

    @staticmethod
    def check_admin_posting(status: Status):
        if Status.ADMIN_POSTING in status and Status.ADMIN not in status:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="Admin posting only",
            )

    async def _handle_info(self, site: SID, model: SiteInfo) -> bool:
        if model is None:
            return False
        else:
            await self.db.execute(
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
                JOIN languages l ON p.default_language_id = l.id
            WHERE p.name = :project
            """,
            values=dict(project=self.project)
        )
        return project_default

    async def _get_random_image(self, site: SID):
        images = list(map(lambda m: m[0], await self.db.fetch_all(
            """
            SELECT i.file_name FROM  sites s
                JOIN memories m ON s.id = m.site_id
                    AND m.published
                JOIN images i ON m.image_id = i.id
            WHERE s.name = :site
            ORDER BY RAND()
            LIMIT 1
            """,
            values=dict(site=site)
        )))
        return random.choice(images) if len(images) > 0 else None

    async def construct_site(self, m) -> Site:
        if m.get("memories_count", 0) > 0 and m.get("image", None) is None:
            m = dict(**m)
            m["image"] = await self._get_random_image(m["id"])
        return Site(location=Point(**m), info=SiteInfo(**m), **m)

    @append_identifier('site', literal=None)
    @require_status(Status.NONE)
    async def all(
            self,
            n: Optional[int] = None,
            lat: Optional[float] = None,
            lon: Optional[float] = None,
            *,
            status: Status,
    ) -> List[Site]:
        values = dict(lang=self.lang, project=self.project, user=self.identity)
        if Status.ADMIN in status:
            where = "WHERE TRUE"
        elif self.authenticated:
            where = "WHERE (s.published OR uc.username = :user)"
        else:
            where = "WHERE s.published"
        if n is not None and lat is not None and lon is not None:
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

    @append_identifier('site', value=True)
    @require_status(
        Status.PUBLISHED,
        Status.EXISTS | Status.ADMIN,
        Status.EXISTS | Status.OWN,
    )
    async def one(self, site: SID, include_memories: bool = False, *, status: Status) -> Site:
        values = dict(
            lang=self.lang, project=self.project, site=site, user=self.identity
        )
        if Status.ADMIN in status:
            where = "WHERE TRUE"
        elif self.authenticated:
            where = "WHERE (s.published OR uc.username = :user)"
        else:
            where = "WHERE s.published"
        m = await self.db.fetch_one(self._select.format(where + " AND s.name = :site"), values=values)
        if m is None:
            raise HTTPException(
                status_code=HTTP_406_NOT_ACCEPTABLE,
                detail="Site missing default localization"
            )
        out = await self.construct_site(m)
        if include_memories:
            out.memories = await MemoryRepo.from_repo(self).all()
        return out

    @append_identifier('site', key='id')
    @require_status(Status.DOES_NOT_EXIST | Status.AUTHENTICATED)
    async def create(self, model: NewSite, status: Status) -> SID:
        SiteRepo.check_admin_posting(status)
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
                published=Status.AUTO_PUBLISH in status,
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

    @append_identifier('site', value=True)
    @require_status(Status.EXISTS | Status.ADMIN, Status.EXISTS | Status.OWN)
    async def modify(self, site: SID, model: ModifiedSite, status: Status) -> bool:
        SiteRepo.check_admin_posting(status)
        data = model.dict(exclude_unset=True)
        modified = False
        modified |= await self._handle_image(site, data)
        if "location" in data:
            modified |= await self._handle_location(site, model.location)
        if "info" in data:
            modified |= await self._handle_info(site, model.info)
        return bool(modified)

    @append_identifier('site', value=True)
    @require_status(Status.OWN, Status.EXISTS | Status.ADMIN)
    async def delete(self, site: SID):
        await self.db.execute(
            """
            DELETE FROM sites WHERE name = :id
            """,
            values=dict(id=site),
        )

    @append_identifier('site', value=True)
    @require_status(Status.EXISTS | Status.ADMIN)
    async def toggle_publish(self, site: SID, publish: bool) -> bool:
        await self.db.execute(
            f'UPDATE sites r'
            f" SET r.published = {1 if publish else 0}"
            f' WHERE r.name = :id AND r.published = {0 if publish else 1}',
            values=dict(id=site),
        )
        return await self.db.fetch_val("SELECT ROW_COUNT()")

    @append_identifier('site', value=True)
    @require_status(Status.PUBLISHED)
    async def report(self, site: SID):
        await self.db.execute(
            """
            INSERT IGNORE INTO audit_sites (site_id, user_id) 
            SELECT s.id, u.id 
            FROM sites s 
                JOIN users u ON u.username = :user
            WHERE s.name = :sid
            """,
            values=dict(user=self.identity, lang=self.lang, sid=site)
        )
