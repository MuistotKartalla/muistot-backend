from .common_imports import *

router = make_router(tags=["Memories"])


@router.get(
    '/projects/{project}/sites/{site}/memories',
    response_model=Memories
)
async def get_memories(r: Request, project: PID, site: SID, db: Database = Depends(dba)) -> Memories:
    repo = MemoryRepo(db, project, site)
    repo.configure(r)
    return Memories(items=await repo.all())


@router.get(
    '/projects/{project}/sites/{site}/memories/{memory}',
    response_model=Memory
)
async def get_memory(r: Request, project: PID, site: SID, memory: MID, db: Database = Depends(dba)) -> Memory:
    repo = MemoryRepo(db, project, site)
    repo.configure(r)
    return await repo.one(memory)


@router.post('/projects/{project}/sites/{site}/memories')
async def new_memory(
        r: Request,
        project: PID,
        site: SID,
        model: NewMemory,
        db: Database = Depends(dba)
) -> JSONResponse:
    repo = MemoryRepo(db, project, site)
    repo.configure(r)
    new_id = await repo.create(model)
    return created(router.url_path_for('get_memory', project=project, site=site, memory=str(new_id)))


@router.patch('/projects/{project}/sites/{site}/memories/{memory}')
@require_auth(scopes.AUTHENTICATED)
async def modify_memory(
        r: Request,
        project: PID,
        site: SID,
        memory: MID,
        model: ModifiedMemory,
        db: Database = Depends(dba)
) -> JSONResponse:
    repo = MemoryRepo(db, project, site)
    repo.configure(r)
    changed = await repo.modify(memory, model)
    return modified(lambda: router.url_path_for('get_memory', project=project, site=site, memory=str(memory)), changed)


@router.delete('/projects/{project}/sites/{site}/memories/{memory}')
@require_auth(scopes.AUTHENTICATED)
async def delete_memory(
        r: Request,
        project: PID,
        site: SID,
        memory: MID,
        db: Database = Depends(dba)
) -> JSONResponse:
    repo = MemoryRepo(db, project, site)
    repo.configure(r)
    await repo.delete(memory)
    return deleted(router.url_path_for('get_memories', project=project, site=site))
