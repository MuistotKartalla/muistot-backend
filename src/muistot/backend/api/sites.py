from typing import Optional

from ._imports import *

router = make_router(tags=["Sites"])


@router.get(
    "/projects/{project}/sites",
    response_model=Sites,
    description=dedent(
        """
        Returns all sites for the current project.
        
        This endpoint can be used in return-all or return nearest mode.
        The return nearest mode is useful if the project has a lot of projects.
        Either all the query parameters have to be specified or none of them.
        """
    ),
    responses=rex.gets(Sites),
)
async def get_sites(
        r: Request,
        project: PID,
        n: Optional[int] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        db: Database = DEFAULT_DB,
) -> Sites:
    repo = SiteRepo(db, project)
    repo.configure(r)
    return Sites(items=await repo.all(n, lat, lon))


@router.get(
    "/projects/{project}/sites/{site}",
    description=dedent(
        """
        Return info for a single Site.
        
        Allows for returning all the memories for the site using a query parameter.
        """
    ),
    responses=rex.get(Site),
)
async def get_site(
        r: Request,
        project: PID,
        site: SID,
        db: Database = DEFAULT_DB,
        include_memories: bool = False,
) -> Site:
    repo = SiteRepo(db, project)
    repo.configure(r)
    return await repo.one(site, include_memories=include_memories)


@router.post(
    "/projects/{project}/sites",
    description=dedent(
        """
        Crates a new site.
        
        This should use the Project default language for localizing the initial information.
        The API currently does not restrict which translation is used as long as the language is enabled.
        """
    ),
    response_class=Response,
    responses=rex.create(True),
)
@require_auth(scopes.AUTHENTICATED)
async def new_site(
        r: Request,
        project: PID,
        model: NewSite = sample(NewSite),
        db: Database = DEFAULT_DB,
):
    repo = SiteRepo(db, project)
    repo.configure(r)
    new_id = await repo.create(model)
    return created(r.url_for("get_site", project=project, site=new_id))


@router.patch(
    "/projects/{project}/sites/{site}",
    description=dedent(
        """
        Modify a site
        
        This endpoint is for modifying site location etc.
        This does not set any defaults.
        """
    ),
    response_class=Response,
    responses=rex.modify(),
)
@require_auth(scopes.AUTHENTICATED)
async def modify_site(
        r: Request,
        project: PID,
        site: SID,
        model: ModifiedSite = sample(ModifiedSite),
        db: Database = DEFAULT_DB,
):
    repo = SiteRepo(db, project)
    repo.configure(r)
    changed = await repo.modify(site, model)
    return modified(lambda: r.url_for("get_site", project=project, site=site), changed)


@router.delete(
    "/projects/{project}/sites/{site}",
    description=dedent(
        """
        Just deletes the site permanently
        """
    ),
    response_class=Response,
    responses=rex.delete(),
)
@require_auth(scopes.AUTHENTICATED)
async def delete_site(
        r: Request,
        project: PID,
        site: SID,
        db: Database = DEFAULT_DB
):
    repo = SiteRepo(db, project)
    repo.configure(r)
    await repo.delete(site)
    return deleted(r.url_for("get_sites", project=project))


@router.put(
    "/projects/{project}/sites/{site}/localize",
    description=dedent(
        """
        This endpoint is used for localizing a site.
        """
    ),
    response_class=Response,
    responses=dict(filter(lambda e: e[0] != 404, rex.modify().items())),
)
@require_auth(scopes.AUTHENTICATED)
async def localize_site(
        r: Request,
        project: PID,
        site: SID,
        info: SiteInfo,
        db: Database = DEFAULT_DB
):
    repo = SiteRepo(db, project)
    repo.configure(r)
    await repo.localize(site, info)
    return Response(
        status_code=204,
        headers=dict(location=r.url_for("get_site", project=project, site=site)),
    )
