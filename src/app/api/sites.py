from .common_imports import *

router = APIRouter()


@router.get('/projects/{project}/sites')
async def get_sites(
        r: Request,
        project: PID,
        n: Optional[int],
        lat: Optional[float],
        lon: Optional[float],
        db: Database = Depends(dba)
) -> List[Site]:
    repo = SiteRepo(db, project)
    repo.configure(r)
    return await repo.all(n, lat, lon)


@router.get('/projects/{project}/sites/{site}')
async def get_site(r: Request, project: PID, site: SID, db: Database = Depends(dba)) -> Site:
    repo = SiteRepo(db, project)
    repo.configure(r)
    return await repo.one(site)


@router.post('/projects/{project}/sites')
async def new_site(r: Request, project: PID, model: NewSite, db: Database = Depends(dba)) -> JSONResponse:
    repo = SiteRepo(db, project)
    repo.configure(r)
    new_id = await repo.create(model)
    return created(router.url_path_for('get_site', project=project, site=new_id))


@router.patch('/projects/{project}/sites/{site}')
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


@router.delete('/projects/{project}/sites/{site}')
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def delete_site(r: Request, project: PID, site: SID, db: Database = Depends(dba)) -> JSONResponse:
    repo = SiteRepo(db, project)
    repo.configure(r)
    await repo.delete(site)
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/projects/{project}/sites/{site}/publish")
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def publish_site(r: Request, project: PID, site: SID, db: Database = Depends(dba)) -> JSONResponse:
    repo = SiteRepo(db, project)
    repo.configure(r)
    await repo.publish(site)
    return JSONResponse(status_code=status.HTTP_200_OK)
