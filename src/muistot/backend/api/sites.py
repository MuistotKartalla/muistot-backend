from textwrap import dedent
from typing import Optional

from fastapi import HTTPException, status, Request, Response, Depends
from pydantic import conint, confloat

from .utils import make_router, rex, deleted, modified, created, sample, require_auth, Repo
from ..models import SID, PID, Site, Sites, NewSite, ModifiedSite
from ..repos import SiteRepo
from ...middleware.language import LanguageMiddleware, LanguageChecker
from ...security import scopes

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
        n: Optional[conint(ge=1)] = None,
        lat: Optional[confloat(ge=0, le=90)] = None,
        lon: Optional[confloat(ge=-180, le=180)] = None,
        repo: SiteRepo = Repo(SiteRepo),
) -> Sites:
    params = [n, lat, lon]
    if not all(map(lambda o: o is None, params)) and not all(map(lambda o: o is not None, params)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Bad Params")
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
        site: SID,
        include_memories: bool = False,
        repo: SiteRepo = Repo(SiteRepo),
) -> Site:
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
        checker: LanguageChecker = Depends(LanguageMiddleware.checker),
        repo: SiteRepo = Repo(SiteRepo),
):
    checker.check(model.info.lang)
    new_id = await repo.create(model)
    return created(r.url_for("get_site", project=project, site=new_id))


@router.patch(
    "/projects/{project}/sites/{site}",
    description=dedent(
        """
        Modify a site
        
        This endpoint is for modifying site location etc.
        This does not set any defaults.
        
        Other users can only modify the description
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
        checker: LanguageChecker = Depends(LanguageMiddleware.checker),
        repo: SiteRepo = Repo(SiteRepo),
):
    if model.info:
        checker.check(model.info.lang)
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
        repo: SiteRepo = Repo(SiteRepo),
):
    await repo.delete(site)
    return deleted(r.url_for("get_sites", project=project))


@router.post(
    "/projects/{project}/sites/{site}/publish",
    description=dedent(
        """
        Toggles published status
        """
    ),
    response_class=Response,
    responses=rex.modify(),
)
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def publish_site(
        r: Request,
        project: PID,
        site: SID,
        publish: bool,
        repo: SiteRepo = Repo(SiteRepo),
):
    changed = await repo.toggle_publish(site, publish)
    return modified(lambda: r.url_for("get_site", project=project, site=site), changed)


@router.put(
    "/projects/{project}/sites/{site}/report",
    description=dedent(
        """
        Reports this site
        """
    ),
    response_class=Response,
    responses=rex.modify(),
)
@require_auth(scopes.AUTHENTICATED)
async def report_site(
        r: Request,
        project: PID,
        site: SID,
        repo: SiteRepo = Repo(SiteRepo),
):
    await repo.report(site)
    return deleted(
        r.url_for(
            "get_site",
            project=project,
            site=site
        )
    )
