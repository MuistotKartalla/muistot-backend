from ._imports import *

router = make_router(tags=["Memories"])


@router.get(
    "/projects/{project}/sites/{site}/memories",
    response_model=Memories,
    description=dedent(
        """
        Returns all memories for a single site.
        
        Optionally returns all comments with the memories.
        """
    ),
    responses=rex.gets(Memories),
)
async def get_memories(
        r: Request,
        project: PID,
        site: SID,
        db: Database = DEFAULT_DB,
) -> Memories:
    repo = MemoryRepo(db, project, site)
    repo.configure(r)
    return Memories(items=await repo.all())


@router.get(
    "/projects/{project}/sites/{site}/memories/{memory}",
    response_model=Memory,
    description=dedent(
        """
        Returns a single memory for a single site.

        Optionally returns all comments with the memory.
        """
    ),
    responses=rex.get(Memory),
)
async def get_memory(
        r: Request,
        project: PID,
        site: SID,
        memory: MID,
        db: Database = DEFAULT_DB,
) -> Memory:
    repo = MemoryRepo(db, project, site)
    repo.configure(r)
    return await repo.one(memory)


@router.post(
    "/projects/{project}/sites/{site}/memories",
    description=dedent(
        """
        Adds a new memory
        """
    ),
    response_class=Response,
    responses=rex.create(),
)
@require_auth(scopes.AUTHENTICATED)
async def new_memory(
        r: Request,
        project: PID,
        site: SID,
        model: NewMemory = sample(NewMemory),
        db: Database = DEFAULT_DB,
):
    repo = MemoryRepo(db, project, site)
    repo.configure(r)
    new_id = await repo.create(model)
    return created(
        r.url_for(
            "get_memory", project=project, site=site, memory=str(new_id)
        )
    )


@router.patch(
    "/projects/{project}/sites/{site}/memories/{memory}",
    description=dedent(
        """
        Allows modifying memories partially
        """
    ),
    response_class=Response,
    responses=rex.modify(),
)
@require_auth(scopes.AUTHENTICATED)
async def modify_memory(
        r: Request,
        project: PID,
        site: SID,
        memory: MID,
        model: ModifiedMemory = sample(ModifiedMemory),
        db: Database = DEFAULT_DB,
):
    repo = MemoryRepo(db, project, site)
    repo.configure(r)
    changed = await repo.modify(memory, model)
    return modified(lambda: r.url_for("get_memory", project=project, site=site, memory=str(memory)), changed)


@router.delete(
    "/projects/{project}/sites/{site}/memories/{memory}",
    description=dedent(
        """
        Soft deletes a memory and sets it invisible for normal users.
        
        Hard delete can be performed by admins from admin interface.
        """
    ),
    response_class=Response,
    responses=rex.delete(),
)
@require_auth(scopes.AUTHENTICATED)
async def delete_memory(
        r: Request,
        project: PID,
        site: SID,
        memory: MID,
        db: Database = DEFAULT_DB
):
    repo = MemoryRepo(db, project, site)
    repo.configure(r)
    await repo.delete(memory)
    return deleted(r.url_for("get_memories", project=project, site=site))


@router.post(
    "/projects/{project}/sites/{site}/memories/{memory}/publish",
    description=dedent(
        """
        Toggles published status
        """
    ),
    response_class=Response,
    responses=rex.modify(),
)
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def publish_memory(
        r: Request,
        project: PID,
        site: SID,
        memory: MID,
        publish: bool,
        db: Database = DEFAULT_DB,
):
    repo = MemoryRepo(db, project, site)
    repo.configure(r)
    changed = await repo.toggle_publish(memory, publish)
    return modified(lambda: r.url_for("get_memory", project=project, site=site, memory=str(memory)), changed)


@router.put(
    "/projects/{project}/sites/{site}/memories/{memory}/report",
    description=dedent(
        """
        REports this memory
        """
    ),
    response_class=Response,
    responses=rex.delete(),
)
@require_auth(scopes.AUTHENTICATED)
async def report_memory(
        r: Request,
        project: PID,
        site: SID,
        memory: MID,
        db: Database = DEFAULT_DB,
):
    repo = MemoryRepo(db, project, site)
    repo.configure(r)
    await repo.report(memory)
    return deleted(
        r.url_for(
            "get_memory",
            project=project,
            site=site,
            memory=str(memory)
        )
    )
