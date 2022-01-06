from .common_imports import *

router = make_router(tags=["Admin"])


@router.put('/projects/publish')
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def publish_project(r: Request, project: PID, db: Database = Depends(dba)):
    repo = ProjectRepo(db)
    repo.configure(r)
    new_id = await repo.publish(project)
    return created(router.url_path_for('get_project', project=new_id))


@router.put("/projects/{project}/sites/publish")
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def publish_site(r: Request, project: PID, site: SID, db: Database = Depends(dba)) -> JSONResponse:
    repo = SiteRepo(db, project)
    repo.configure(r)
    new_id = await repo.publish(site)
    return created(router.url_path_for('get_site', project=project, site=new_id))
