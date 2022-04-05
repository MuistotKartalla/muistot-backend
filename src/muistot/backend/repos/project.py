from .base import *
from .exists import check
from .site import SiteRepo


def _check_start(m) -> bool:
    return m["start_date"] == 1


class ProjectRepo(BaseRepo):
    _select = """
        SELECT

            p.id AS project_id,
            p.name AS id,
            i.file_name AS image,
            IFNULL(l.lang, def_l.lang) AS lang,
            COALESCE(pi.name, def_pi.name, p.name)AS name,
            IFNULL(pi.abstract, def_pi.abstract) AS abstract,
            IFNULL(pi.description, def_pi.description) AS description,
            p.starts,
            p.ends,
            pc.has_research_permit,
            pc.contact_email,
            COUNT(s.id) AS sites_count,
            
            IFNULL(p.starts > CURDATE(), TRUE) AS start_date

        FROM projects p

            LEFT JOIN project_information pi 
                JOIN languages l ON pi.lang_id = l.id
                    AND l.lang = :lang
                ON p.id = pi.project_id

            JOIN project_information def_pi
                ON p.id = def_pi.project_id
                    AND def_pi.lang_id = p.default_language_id
            JOIN languages def_l ON def_pi.lang_id = def_l.id
                

            LEFT JOIN images i ON p.image_id = i.id
            LEFT JOIN project_contact pc ON p.id = pc.project_id
            LEFT JOIN sites s ON p.id = s.project_id
                AND s.published
                
        WHERE TRUE %s
        GROUP BY p.id
        """

    async def _get_admins(self, project_id: int):
        out = [
            admin[0]
            for admin in await self.db.fetch_all(
                """
            SELECT u.username
            FROM project_admins pa
                JOIN users u ON pa.user_id = u.id
            WHERE project_id = :pid
            """,
                values=dict(pid=project_id),
            )
        ]
        return out if len(out) > 0 else list()

    async def _handle_localization(self, project: PID, localized_data: ProjectInfo):
        if localized_data is not None:
            await self.db.execute(
                """
                REPLACE INTO project_information (
                    project_id, 
                    lang_id,
                    name, 
                    abstract,
                    description, 
                    modifier_id
                ) 
                SELECT 
                    p.id, 
                    l.id, 
                    :name, 
                    :abstract, 
                    :description, 
                    u.id
                FROM projects p
                    JOIN languages l ON l.lang = :lang
                    JOIN users u ON u.username = :user
                WHERE p.name = :project
                """,
                values=dict(
                    **localized_data.dict(
                        include={"name", "abstract", "description", "lang"}
                    ),
                    user=self.identity,
                    project=project,
                ),
            )

    async def _handle_contact(self, project: PID, contact: Optional[ProjectContact]):
        if contact is not None:
            await self.db.execute(
                """
                REPLACE INTO project_contact (
                    project_id, 
                    modifier_id,
                    can_contact, 
                    has_research_permit, 
                    contact_email
                ) 
                SELECT
                    p.id,
                    u.id,
                    :can_contact,
                    :has_research_permit,
                    :contact_email
                FROM projects p
                    JOIN users u ON u.username = :user
                WHERE p.name = :project
                """,
                values=dict(**contact.dict(), user=self.identity, project=project),
            )

    async def _handle_admins(self, project: PID, admins: List[str]):
        if admins is not None and len(admins) > 0:
            await self.db.execute(
                f"""
                INSERT INTO project_admins (project_id, user_id)
                SELECT p.id, u.id
                FROM users u
                    JOIN projects p ON p.name = :project
                WHERE u.username IN ({",".join(f":admin_{i}" for i in range(0, len(admins)))})
                """,
                values=dict(
                    project=project, **{f"admin_{i}": v for i, v in enumerate(admins)}
                ),
            )

    async def construct_project(self, m) -> Project:
        pi = ProjectInfo(**m)
        if not m[8] is None:
            pc = ProjectContact(**m)
        else:
            pc = None
        return Project(**m, info=pi, contact=pc, admins=await self._get_admins(m[0]))

    async def all(self) -> List[Project]:
        return [
            await self.construct_project(m)
            for m in await self.db.fetch_all(self._select % " AND p.published", values=dict(lang=self.lang))
            if m is not None and _check_start(m)
        ]

    @check.published_or_admin
    async def one(self, project: PID, include_sites: bool = False) -> Project:
        m = await self.db.fetch_one(
            self._select % " AND p.name = :project",
            values=dict(lang=self.lang, project=project)
        )
        if m is None:
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail='Project missing default localization'
            )
        elif not _check_start(m):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Project not found'
            )
        out = await self.construct_project(m)
        if include_sites:
            out.sites = await SiteRepo(self.db, project).from_repo(self).all()
        return out

    @check.not_exists
    async def create(self, model: NewProject) -> PID:
        if not self.superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")
        check_language(model.info.lang)
        if (
                model.starts is not None
                and model.ends is not None
                and model.starts <= model.ends
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End before start")

        image_id = await self.files.handle(model.image)
        await self.db.execute(
            """
            INSERT INTO projects (
                    modifier_id,
                    default_language_id,
                    image_id,
                    published,
                    name,
                    starts,
                    ends,
                    admin_posting
            )
            SELECT u.id,
                   l.id,
                   :image_id,
                   :published,
                   :id,
                   :starts,
                   :ends,
                   :admin_posting
            FROM users u
                     JOIN languages l ON l.lang = :lang
            WHERE u.username = :user
            """,
            values=dict(
                **model.dict(include={"id", "starts", "ends", "admin_posting"}),
                image_id=image_id,
                user=self.identity,
                lang=model.info.lang,
                published=self.auto_publish,
            ),
        )
        if model.contact is not None:
            await self._handle_contact(model.id, model.contact)
        if model.info is not None:
            await self._handle_localization(model.id, model.info)
        if model.admins is not None:
            await self._handle_admins(model.id, model.admins)
        return model.id

    @check.admin
    async def modify(self, project: PID, model: ModifiedProject) -> bool:
        data = model.dict(exclude_unset=True)
        if len(data) == 0:
            return False
        else:
            values = {}
            if "image" in data:
                values["image_id"] = await self.files.handle(model.image)
            if "contact" in data:
                await self._handle_contact(project, model.contact)
            for k in {"starts", "ends"}:
                if k in data:
                    values[k] = data[k]
            if len(values) > 0:
                await self.db.fetch_val(
                    f"""
                    UPDATE projects p
                        LEFT JOIN users u ON u.username = :user
                    SET {",".join(f"p.{k}=:{k}" for k in values.keys())},
                        p.modifier_id = u.id
                    WHERE p.name = :project
                    """,
                    values=dict(**values, project=project, user=self.identity),
                )
                modified = True
            else:
                modified = False
            return modified

    @check.zuper
    async def delete(self, project: PID):
        await self.db.execute(
            """
            DELETE FROM projects WHERE name = :project
            """,
            values=dict(project=project),
        )

    @check.admin
    async def toggle_publish(self, project: PID, publish: bool):
        await self._set_published(publish, name=project)

    @check.admin
    async def localize(self, project: PID, localized_data: ProjectInfo):
        await self._handle_localization(project, localized_data)

    @check.admin
    async def add_admin(self, project: PID, user: UID):
        m = await self.db.fetch_one(
            """
            SELECT ISNULL(uu.id), NOT ISNULL(pa.user_id)
            FROM projects p
                LEFT JOIN project_admins pa
                        JOIN users u ON pa.user_id = u.id AND u.username = :user
                    ON p.id = pa.project_id
                LEFT JOIN users uu ON uu.username = :user
            WHERE p.name = :project
            """,
            values=dict(user=user, project=project),
        )
        if m[0]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        elif m[1]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="User is already an admin"
            )
        else:
            await self.db.execute(
                """
                INSERT INTO project_admins (project_id, user_id)
                SELECT p.id, u.id 
                FROM users u 
                    JOIN projects p ON p.name = :project 
                WHERE u.username = :user
                """,
                values=dict(project=project, user=user),
            )

    @check.admin
    async def delete_admin(self, project: PID, user: UID):
        if await self.db.fetch_val(
                "SELECT NOT EXISTS(SELECT 1 FROM users WHERE username = :user)",
                values=dict(user=user),
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        await self.db.execute(
            """
            DELETE pa FROM project_admins pa
                JOIN users u ON u.id = pa.user_id
                JOIN projects p ON  p.id = pa.project_id
            WHERE u.username = :user AND p.name = :project
            """,
            values=dict(project=project, user=user),
        )
