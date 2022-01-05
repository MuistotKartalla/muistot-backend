from .common_imports import *

router = APIRouter()


@router.get('/projects')
async def get_projects(db: Database = Depends(dba)) -> List[Project]:
    repo = ProjectRepo(db)
    return await repo.all()


@router.get('/projects/{project}')
async def get_project(project: PID, db: Database = Depends(dba)) -> Project:
    repo = ProjectRepo(db)
    return await repo.one(project)


@router.post('/projects')
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def new_project(r: Request, model: Project, db: Database = Depends(dba)):
    repo = ProjectRepo(db)
    repo.set_user(r.user)
    new_id = await repo.create(model)
    return created(router.url_path_for('get_project', project=new_id))


@router.patch('/projects/{project}')
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def modify_project(r: Request, project: PID, model: ModifiedProject, db: Database = Depends(dba)) -> JSONResponse:
    repo = ProjectRepo(db)
    repo.set_user(r.user)
    changed = await repo.modify(project, model)
    return modified(lambda: router.url_path_for('get_project', project=project), changed)


@router.delete('/projects/{project}')
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def delete_project(r: Request, project: PID, db: Database = Depends(dba)) -> JSONResponse:
    repo = ProjectRepo(db)
    repo.set_user(r.user)
    await repo.delete(project)
    return deleted(router.url_path_for('get_projects'))
