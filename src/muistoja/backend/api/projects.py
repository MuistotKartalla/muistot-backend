from .common_imports import *

router = make_router(tags=["Projects"])


@router.get(
    '/projects',
    response_model=Projects,
    description=(
            """
            This endpoint returns all projects that are currently running and published.
            
            Does not allow for any configuration parameters.
            The amount of data returned might differ slightly based on the user permissions.
            """
    )
)
async def get_projects(r: Request, db: Database = Depends(dba)) -> Projects:
    repo = ProjectRepo(db)
    repo.configure(r)
    return Projects(items=await repo.all())


@router.get(
    '/projects/{project}',
    response_model=Project,
    description=(
            """
            This endpoint returns the information for a single Project
            
            It is possible to query all the sites at the same time too.
            An error message will be returned if the project is not published or active.
            """
    )
)
async def get_project(
        r: Request,
        project: PID,
        db: Database = Depends(dba),
        include_sites: bool = False
) -> Project:
    repo = ProjectRepo(db)
    repo.configure(r)
    return await repo.one(project, include_sites=include_sites)


@router.post(
    '/projects',
    description=(
            """
            This endpoint is used for Project creation.
            
            This will only work for SuperUsers in the API.
            The Project object will set the default language for the project based on the ProjectInfo embedded into it.
            Projects use the default language to try and finds default info objects in case user language is not supported.
            The idea is to localize all sites with the default language, but this is not enforced in the API.
            
            TODO: There is also a possibility of specifying anonymous posting, but this is not implemented properly in the api yet.
            """
    )
)
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def new_project(r: Request, model: NewProject, db: Database = Depends(dba)):
    repo = ProjectRepo(db)
    repo.configure(r)
    new_id = await repo.create(model)
    return created(router.url_path_for('get_project', project=new_id))


@router.patch(
    '/projects/{project}',
    description=(
            """
            This is used for patching core Project attributes.
            
            This will override the defaults set during creation for language so be careful.
            The idea is to use a localization endpoint to add translations and only use this for modifying core info.
            """
    )
)
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def modify_project(r: Request, project: PID, model: ModifiedProject, db: Database = Depends(dba)) -> JSONResponse:
    repo = ProjectRepo(db)
    repo.configure(r)
    changed = await repo.modify(project, model)
    return modified(lambda: router.url_path_for('get_project', project=project), changed)


@router.delete(
    '/projects/{project}',
    description=(
            """
            Soft Deletes a project by hiding it from regular users.
            
            The actual deletion has to be done by a maintainer or from the Admin interface.
            """
    )
)
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def delete_project(r: Request, project: PID, db: Database = Depends(dba)) -> JSONResponse:
    repo = ProjectRepo(db)
    repo.configure(r)
    await repo.toggle_publish(project, False)
    return deleted(router.url_path_for('get_projects'))
