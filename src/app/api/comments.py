from .common_imports import *

router = make_router()


@router.get(
    '/projects/{project}/sites/{site}/comments',
    response_model=Comments
)
async def get_comments(
        r: Request,
        project: PID,
        site: SID,
        memory: MID,
        db: Database = Depends(dba)
) -> Comments:
    repo = CommentRepo(db, project, site, memory)
    repo.configure(r)
    return Comments(items=await repo.all())


@router.get(
    '/projects/{project}/sites/{site}/comments/{comment}',
    response_model=Comment
)
async def get_comment(
        r: Request,
        project: PID,
        site: SID,
        memory: MID,
        comment: CID,
        db: Database = Depends(dba)
) -> Comment:
    repo = CommentRepo(db, project, site, memory)
    repo.configure(r)
    return await repo.one(comment)


@router.post('/projects/{project}/sites/{site}/comments')
@require_auth(scopes.AUTHENTICATED)
async def new_comment(
        r: Request,
        project: PID,
        site: SID,
        memory: MID,
        model: NewComment,
        db: Database = Depends(dba)
) -> JSONResponse:
    repo = CommentRepo(db, project, site, memory)
    repo.configure(r)
    new_id = repo.create(model)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        headers={
            LOCATION: router.url_path_for(
                'get_comment',
                project=project,
                site=site,
                memory=str(memory),
                comment=str(new_id)
            )}
    )


@router.patch('/projects/{project}/sites/{site}/comments/{comment}')
@require_auth(scopes.AUTHENTICATED)
async def modify_comment(
        r: Request,
        project: PID,
        site: SID,
        memory: MID,
        comment: CID,
        model: ModifiedComment,
        db: Database = Depends(dba)
) -> JSONResponse:
    repo = CommentRepo(db, project, site, memory)
    repo.configure(r)
    changed = await repo.modify(comment, model)
    return modified(lambda: router.url_path_for(
        'get_comment',
        project=project,
        site=site,
        memory=str(memory),
        comment=str(comment)
    ), changed)


@router.delete('/projects/{project}/sites/{site}/comments/{comment}')
@require_auth(scopes.AUTHENTICATED)
async def delete_comment(
        r: Request,
        project: PID,
        site: SID,
        memory: MID,
        comment: CID,
        db: Database = Depends(dba)
) -> JSONResponse:
    repo = CommentRepo(db, project, site, memory)
    repo.configure(r)
    await repo.delete(comment)
    return deleted(router.url_path_for(
        'get_comments',
        project=project,
        site=site,
        memory=str(memory),
    ))
