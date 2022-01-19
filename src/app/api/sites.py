from .common_imports import *

router = make_router(tags=["Sites"])


@router.get(
    '/projects/{project}/sites',
    response_model=Sites,
    description=(
        """
        Returns all sites for the current project.
        
        This endpoint can be used in return-all or return nearest mode.
        The return nearest mode is useful if the project has a lot of projects.
        Either all the query parameters have to be specified or none of them.
        """
    )
)
async def get_sites(
        r: Request,
        project: PID,
        n: Optional[int] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        db: Database = Depends(dba)
) -> Sites:
    repo = SiteRepo(db, project)
    repo.configure(r)
    return Sites(items=await repo.all(n, lat, lon))


@router.get(
    '/projects/{project}/sites/{site}',
    description=(
        """
        Return info for a single Site.
        
        Allows for returning all the memories for the site using a query parameter.
        """
    )
)
async def get_site(
        r: Request,
        project: PID,
        site: SID,
        db: Database = Depends(dba),
        include_memories: bool = False
) -> Site:
    repo = SiteRepo(db, project)
    repo.configure(r)
    return await repo.one(site, include_memories=include_memories)


@router.post(
    '/projects/{project}/sites',
    description=(
        """
        Crates a new site.
        
        This should use the Project default language for localizing the initial information.
        The API currently does not restrict which translation is used as long as the language is enabled.
        """
    )
)
async def new_site(r: Request, project: PID, model: NewSite, db: Database = Depends(dba)) -> JSONResponse:
    repo = SiteRepo(db, project)
    repo.configure(r)
    new_id = await repo.create(model)
    return created(router.url_path_for('get_site', project=project, site=new_id))


@router.patch(
    '/projects/{project}/sites/{site}',
    description=(
        """
        Modify a site
        
        This endpoint is for modifying site location etc.
        This does not set any defaults.
        """
    )
)
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def modify_site(
        r: Request,
        project: PID,
        site: SID,
        model: ModifiedSite,
        db: Database = Depends(dba)
) -> JSONResponse:
    repo = SiteRepo(db, project)
    repo.configure(r)
    changed = await repo.modify(site, model)
    return modified(lambda: router.url_path_for('get_site', project=project, site=site), changed)


@router.delete(
    '/projects/{project}/sites/{site}',
    description=(
        """
        Soft deletes a Site and hides it from normal users.
        
        Actual deletion can only be done by a maintainer or from the admin interface.
        """
    )
)
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def delete_site(r: Request, project: PID, site: SID, db: Database = Depends(dba)) -> JSONResponse:
    repo = SiteRepo(db, project)
    repo.configure(r)
    await repo.toggle_publish(site, False)
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)
