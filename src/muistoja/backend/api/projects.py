from itertools import chain

from ._imports import *

router = make_router(tags=["Projects"])


@router.get(
    "/projects",
    response_model=Projects,
    description=dedent(
        """
        This endpoint returns all projects that are currently running and published.
        
        Does not allow for any configuration parameters.
        The amount of data returned might differ slightly based on the user permissions.
        """
    ),
    responses=dict(filter(lambda e: e[0] != 404, rex.gets(Projects).items())),
)
async def get_projects(
        r: Request,
        db: Database = DEFAULT_DB
) -> Projects:
    repo = ProjectRepo(db)
    repo.configure(r)
    return Projects(items=await repo.all())


@router.get(
    "/projects/{project}",
    response_model=Project,
    description=dedent(
        """
        This endpoint returns the information for a single Project
        
        It is possible to query all the sites at the same time too.
        An error message will be returned if the project is not published or active.
        """
    ),
    responses=dict(
        chain(
            filter(lambda e: e[0] != 404, rex.get(Project).items()),
            [(404, d("Resource found"))],
        )
    ),
)
async def get_project(
        r: Request,
        project: PID,
        db: Database = DEFAULT_DB,
        include_sites: bool = False
) -> Project:
    repo = ProjectRepo(db)
    repo.configure(r)
    return await repo.one(project, include_sites=include_sites)


@router.post(
    "/projects",
    description=dedent(
        """
        This endpoint is used for Project creation.
        
        This will only work for SuperUsers in the API.
        The Project object will set the default language for the project based on the ProjectInfo embedded into it.
        Projects use the default language to try and finds default info objects in case user language is not supported.
        The idea is to localize all sites with the default language, but this is not enforced in the API.
        """
    ),
    response_class=Response,
    responses=dict(filter(lambda e: e[0] != 404, rex.create(True).items())),
)
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def new_project(
        r: Request,
        model: NewProject = sample(NewProject),
        db: Database = DEFAULT_DB
):
    repo = ProjectRepo(db)
    repo.configure(r)
    new_id = await repo.create(model)
    return created(router.url_path_for("get_project", project=new_id))


@router.patch(
    "/projects/{project}",
    description=dedent(
        """
        This is used for patching core Project attributes.
        
        This will override the defaults set during creation for language so be careful.
        The idea is to use a localization endpoint to add translations and only use this for modifying core info.
        """
    ),
    response_class=Response,
    responses=dict(
        chain(
            filter(lambda e: e[0] != 404, rex.modify().items()),
            [(404, d("Resource found"))],
        )
    ),
)
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def modify_project(
        r: Request,
        project: PID,
        model: ModifiedProject = sample(ModifiedProject),
        db: Database = DEFAULT_DB,
):
    repo = ProjectRepo(db)
    repo.configure(r)
    changed = await repo.modify(project, model)
    return modified(
        lambda: router.url_path_for("get_project", project=project), changed
    )


@router.delete(
    "/projects/{project}",
    description=dedent(
        """
        Soft Deletes a project by hiding it from regular users.
        
        The actual deletion has to be done by a maintainer or from the Admin interface.
        """
    ),
    response_class=Response,
    responses=dict(filter(lambda e: e[0] != 404, rex.delete().items())),
)
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def delete_project(
        r: Request,
        project: PID,
        db: Database = DEFAULT_DB
):
    repo = ProjectRepo(db)
    repo.configure(r)
    await repo.toggle_publish(project, False)
    return deleted(router.url_path_for("get_projects"))


@router.post(
    "/projects/{project}/admins",
    description=dedent(
        """
        This endpoint is used for adding admins to a project.
        """
    ),
    response_class=Response,
    responses=rex.create(False),
)
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def add_project_admin(
        r: Request,
        project: PID,
        username: UID,
        db: Database = DEFAULT_DB
):
    repo = ProjectRepo(db)
    repo.configure(r)
    await repo.add_admin(project, username)
    return Response(
        status_code=200,
        headers=dict(location=router.url_path_for("get_project", project=project)),
    )


@router.delete(
    "/projects/{project}/admins",
    description=dedent(
        """
        This endpoint is used for deleting admins from a project.
        """
    ),
    response_class=Response,
    responses=rex.delete(),
)
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def delete_project_admin(
        r: Request,
        project: PID,
        username: UID,
        db: Database = DEFAULT_DB
):
    repo = ProjectRepo(db)
    repo.configure(r)
    await repo.delete_admin(project, username)
    return Response(
        status_code=204,
        headers=dict(location=router.url_path_for("get_project", project=project)),
    )


@router.put(
    "/projects/{project}/localize",
    description=dedent(
        """
        This endpoint is used for localizing a project.
        """
    ),
    response_class=Response,
    responses=dict(filter(lambda e: e[0] != 404, rex.create(True).items())),
)
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def localize_project(
        r: Request,
        project: PID,
        info: ProjectInfo,
        db: Database = DEFAULT_DB
):
    repo = ProjectRepo(db)
    repo.configure(r)
    await repo.localize(project, info)
    return Response(
        status_code=201,
        headers=dict(location=router.url_path_for("get_project", project=project)),
    )
