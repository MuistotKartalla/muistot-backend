from .base import *
from .exists import check, Status


def _check_dates(m) -> bool:
    return m["start_date"] == 1 and m["end_date"] == 1


class ProjectRepo(BaseRepo):
    _select = """
        SELECT

            p.id                                                AS project_id,
            p.name                                              AS id,
            i.file_name                                         AS image,
            IFNULL(l.lang, def_l.lang)                          AS lang,
            COALESCE(pi.name, def_pi.name, p.name)              AS name,
            IFNULL(pi.abstract, def_pi.abstract)                AS abstract,
            IFNULL(pi.description, def_pi.description)          AS description,
            p.starts,
            p.ends,
            NOT ISNULL(pc.project_id)                           AS has_contact_data,
            pc.has_research_permit,
            pc.contact_email,
            pc.can_contact,
            
            COUNT(s.id)                                         AS sites_count,
            
            IF(p.starts IS NULL, TRUE, p.starts < CURDATE())    AS start_date,
            IF(p.ends IS NULL, TRUE, p.ends > CURDATE())        AS end_date

            %s
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
            %s
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
            return True
        return False

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
        else:
            await self.db.execute(
                """
                DELETE FROM project_contact
                WHERE project_id = (SELECT id FROM projects WHERE name = :project)
                """,
                values=dict(project=project)
            )
        return True

    async def _handle_admins(self, project: PID, admins: List[str]):
        if admins is not None and len(admins) > 0:
            data = await self.db.fetch_all(
                f"""
                SELECT u.username, u.id 
                FROM users u 
                WHERE u.username IN ({",".join(f":admin_{i}" for i in range(0, len(admins)))})
                """,
                values=dict(
                    project=project, **{f"admin_{i}": v for i, v in enumerate(admins)}
                )
            )
            not_found = [name for name in admins if name not in set(map(lambda m: m[0], data))]
            if len(not_found) != 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Admins not found" + ("\n".join(map(lambda t: t[1], not_found)))
                )
            pid = await self.db.fetch_val("SELECT id FROM projects WHERE name = :name", values=dict(name=project))
            await self.db.execute(
                f"""
                INSERT INTO project_admins (project_id, user_id)
                    VALUES {",".join(f"(:pid, :admin_{i})" for i in range(0, len(data)))}
                """,
                values=dict(
                    pid=pid, **{f"admin_{i}": v[1] for i, v in enumerate(data)}
                ),
            )

    async def construct_project(self, m) -> Project:
        pi = ProjectInfo(**m)
        if m["has_contact_data"]:
            pc = ProjectContact(**m)
        else:
            pc = None
        return Project(**m, info=pi, contact=pc, admins=await self._get_admins(m[0]))

    async def all(self) -> List[Project]:
        return [
            await self.construct_project(m)
            for m in await self.db.fetch_all(
                self._select % (
                    ",IFNULL(au.id, su.id) IS NOT NULL AS is_admin",
                    """
                    LEFT JOIN users su JOIN superusers sus ON sus.user_id = su.id ON su.username = :user
                    LEFT JOIN users au JOIN project_admins pa ON pa.user_id = au.id ON au.username = :user
                    """,
                    """
                     AND p.published OR au.id IS NOT NULL OR su.id IS NOT NULL
                    """
                )
                if self.authenticated else
                self._select % ("", "", " AND p.published"),
                values=
                dict(lang=self.lang)
                if not self.authenticated else
                dict(lang=self.lang, user=self.identity)

            )
            if m is not None and (_check_dates(m) or (self.superuser or m["is_admin"] if self.authenticated else False))
        ]

    @check.published_or_admin
    async def one(self, project: PID, _status: Status = None) -> Project:
        m = await self.db.fetch_one(
            self._select % ("", "", " AND p.name = :project"),
            values=dict(lang=self.lang, project=project)
        )
        if m is None:
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail='Project missing default localization'
            )
        elif not _check_dates(m) and not _status.admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Project not found'
            )
        out = await self.construct_project(m)
        return out

    @check.not_exists
    async def create(self, model: NewProject) -> PID:
        if not self.superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")
        check_language(model.info.lang)
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
        await self._handle_localization(model.id, model.info)
        await self._handle_admins(model.id, model.admins)
        if model.contact is not None:
            await self._handle_contact(model.id, model.contact)
        return model.id

    @check.admin
    async def modify(self, project: PID, model: ModifiedProject) -> bool:
        data = model.dict(exclude_unset=True)
        if len(data) == 0:
            return False
        else:
            values = {}
            modified = False
            if "image" in data:
                values["image_id"] = await self.files.handle(model.image)
            if "contact" in data:
                modified = await self._handle_contact(project, model.contact)
            if "info" in data:
                modified = await self._handle_localization(project, model.info)
            if "default_language" in data:
                lang = data["default_language"]
                check_language(lang)
                values["default_language_id"] = await self.db.fetch_val(
                    "SELECT id FROM languages WHERE lang = :lang",
                    values=dict(lang=lang)
                )
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
    async def toggle_publish(self, project: PID, publish: bool) -> bool:
        await self.db.execute(
            f'UPDATE projects r'
            f" SET r.published = {1 if publish else 0}"
            f' WHERE r.name = :id',
            values=dict(id=project),
        )
        return await self.db.fetch_val("SELECT ROW_COUNT()")

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
