from .utils import *
from .site import SiteRepo


class ProjectRepo(BaseRepo):
    _select = (
        """
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
            COUNT(s.id) AS site_count

        FROM projects p

            LEFT JOIN project_information pi 
                JOIN languages l ON pi.lang_id = l.id
                    AND l.lang = :lang
                ON p.id = pi.project_id

            LEFT JOIN project_information def_pi 
                JOIN languages def_l ON def_pi.lang_id = def_l.id
                ON p.id = def_pi.project_id
                    AND def_pi.lang_id = p.default_language_id

            LEFT JOIN images i ON p.image_id = i.id
            LEFT JOIN project_contact pc ON p.id = pc.project_id
            LEFT JOIN sites s ON p.id = s.project_id
                AND s.published

        WHERE IFNULL(p.starts > CURDATE(), TRUE) AND p.published
        GROUP BY p.id
        """
    )

    async def _get_admins(self, project_id: int):
        out = [admin[0] for admin in await self.db.fetch_all(
            """
            SELECT u.username
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

    async def _handle_localization(self, project: PID, localized_data: ProjectInfo) -> int:
        if not self.user.is_authenticated:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authorized to update')
        return await self.db.fetch_val(
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
            RETURNING l.id
            """,
            values=dict(
                **localized_data.dict(include={'name', 'abstract', 'description', 'lang'}),
                user=self.user.identity,
                project=project
            )
        )

    async def _handle_contact(self, project: PID, contact: Optional[ProjectContact]):
        if contact is None:
            return
        if not self.user.is_authenticated:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authorized to update')
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
            values=dict(
                **contact.dict(),
                user=self.user.identity,
                project=project
            )
        )

    async def _handle_admins(self, project: PID, admins: List[str]):
        await self.db.execute(
            "DELETE FROM project_admins WHERE project_id = (SELECT id FROM projects WHERE name = :project)",
            values=dict(project=project)
        )
        await self.db.execute(
            f"""
            REPLACE INTO project_admins (project_id, user_id)
            SELECT p.id, u.id
            FROM users u
                JOIN projects p ON p.name = :project
            WHERE u.username IN ({",".join(f"admin_{i}" for i in range(0, len(admins)))})
            """,
            values=dict(
                project=project,
                **{
                    f"admin_{i}": v for i, v in enumerate(admins)
                }
            )
        )

    @check_lang
    async def construct_project(self, m) -> Project:
        if m is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Project not found'
            )
        pi = ProjectInfo(**m)
        if not m[8] is None:
            pc = ProjectContact(**m)
        else:
            pc = None
        return Project(
            **m,
            info=pi,
            contact=pc,
            admins=await self._get_admins(m[0])
        )

    async def all(self) -> List[Project]:
        return [await self.construct_project(m) for m in await self.db.fetch_all(
            self._select,
            values=dict(lang=self.lang)
        ) if m is not None]

    @check_exists
    async def one(self, project: PID, include_sites: bool = False) -> Project:
        out = await self.construct_project(await self.db.fetch_one(
            self._select + " AND p.name = :project",
            values=dict(lang=self.lang, project=project)
        ))
        if include_sites:
            out.sites = SiteRepo(self.db, project).all()
        return out

    @needs_admin
    @check_not_exists
    async def create(self, model: NewProject) -> PID:

        check_id(model.id)
        check_language(model.info.lang)
        if model.starts is not None and model.ends is not None and model.starts <= model.ends:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='End before start')
        if model.image is not None:
            image_id = await Files(self.db, self.user).handle(model.image)
        else:
            image_id = None
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
                    anonymous_posting
            )
            SELECT u.id,
                   l.id,
                   :id,
                   :image_id,
                   :starts,
                   :ends,
                   :anonymous_posting,
                   :published
            FROM users u
                     JOIN languages l ON l.lang = :lang
            WHERE u.username = :user
            """,
            values=dict(
                **model.dict(include={'name', 'starts', 'ends', 'anonymous_posting'}),
                image_id=image_id,
                user=self.user.identity,
                lang=model.info.lang,
                published=Config.auto_publish
            )
        )
        if model.contact is not None:
            await self._handle_contact(model.id, model.contact)
        if model.info is not None:
            await self._handle_localization(model.id, model.info)
        if model.admins is not None:
            await self._handle_admins(model.id, model.admins)
        return model.id

    @needs_admin
    @check_exists
    async def modify(self, project: PID, model: ModifiedProject) -> bool:
        data = model.dict(exclude_unset=True)
        if len(data) == 0:
            return False
        else:
            values = {}
            if 'image' in data:
                values['image_id'] = await Files(self.db, self.user).handle(model.image)
            if 'contact' in data:
                await self._handle_contact(project, model.contact)
            if 'info' in data:
                values["default_language_id"] = await self._handle_localization(project, model.info)
            for k in {'starts', 'ends'}:
                if k in data:
                    values[k] = data[k]
            if len(values) > 0:
                modified = await self.db.fetch_val(
                    f"""
                    UPDATE projects p
                    SET {",".join(f"{k}=:{k}" for k in values.keys())} 
                    WHERE p.name = :project
                    """,
                    values=dict(**values, project=project)
                )
            else:
                modified = False
            if model.admins is not None:
                await self._handle_admins(project, model.admins)
                modified = True
            return modified

    @needs_admin
    async def delete(self, project: PID):
        await self.db.execute(
            """
            DELETE FROM projects WHERE name = :project
            """,
            values=dict(project=project)
        )

    @needs_admin
    @check_exists
    async def toggle_publish(self, project: PID, publish: bool):
        await self._set_published(publish, name=project)

    @needs_admin
    @check_exists
    async def localize(self, project: PID, localized_data: ProjectInfo):
        await self._handle_localization(project, localized_data)
