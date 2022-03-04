from ._imports import *

router = make_router(tags=["Comments"])


@router.get(
    "/projects/{project}/sites/{site}/memories/{memory}/comments",
    response_model=Comments,
    description=dedent(
        """
        Returns all comments for a memory.
        """
    ),
    responses=rex.gets(Comments),
)
async def get_comments(
        r: Request,
        project: PID,
        site: SID,
        memory: MID,
        db: Database = DEFAULT_DB
) -> Comments:
    repo = CommentRepo(db, project, site, memory)
    repo.configure(r)
    return Comments(items=await repo.all())


@router.get(
    "/projects/{project}/sites/{site}/memories/{memory}/comments/{comment}",
    response_model=Comment,
    description=dedent(
        """
        Returns all relevant data for a single comment.
        """
    ),
    responses=rex.get(Comment),
)
async def get_comment(
        r: Request,
        project: PID,
        site: SID,
        memory: MID,
        comment: CID,
        db: Database = DEFAULT_DB,
) -> Comment:
    repo = CommentRepo(db, project, site, memory)
    repo.configure(r)
    return await repo.one(comment)


@router.post(
    "/projects/{project}/sites/{site}/memories/{memory}/comments",
    description=dedent(
        """
        Adds a new comment to a site.
        """
    ),
    responses=rex.create(),
    response_class=Response,
)
@require_auth(scopes.AUTHENTICATED)
async def new_comment(
        r: Request,
        project: PID,
        site: SID,
        memory: MID,
        model: NewComment = sample(NewComment),
        db: Database = DEFAULT_DB,
):
    repo = CommentRepo(db, project, site, memory)
    repo.configure(r)
    new_id = await repo.create(model)
    return created(
        r.url_for(
            "get_comment",
            project=project,
            site=site,
            memory=str(memory),
            comment=str(new_id),
        )
    )


@router.patch(
    "/projects/{project}/sites/{site}/memories/{memory}/comments/{comment}",
    description=dedent(
        """
        Edits a comment.
        
        Currently only the Author and a SuperUser can modify the comment.
        """
    ),
    responses=rex.modify(),
    response_class=Response,
)
@require_auth(scopes.AUTHENTICATED)
async def modify_comment(
        r: Request,
        project: PID,
        site: SID,
        memory: MID,
        comment: CID,
        model: ModifiedComment = sample(ModifiedComment),
        db: Database = DEFAULT_DB,
):
    repo = CommentRepo(db, project, site, memory)
    repo.configure(r)
    changed = await repo.modify(comment, model)
    return modified(
        lambda: r.url_for(
            "get_comment",
            project=project,
            site=site,
            memory=str(memory),
            comment=str(comment),
        ),
        changed,
    )


@router.delete(
    "/projects/{project}/sites/{site}/memories/{memory}/comments/{comment}",
    description=dedent(
        """
        Permanently deletes a comment.
        
        This can be done by the author or an admin.
        """
    ),
    response_class=Response,
    responses=rex.delete(),
)
@require_auth(scopes.AUTHENTICATED)
async def delete_comment(
        r: Request,
        project: PID,
        site: SID,
        memory: MID,
        comment: CID,
        db: Database = DEFAULT_DB,
):
    repo = CommentRepo(db, project, site, memory)
    repo.configure(r)
    await repo.delete(comment)
    return deleted(
        r.url_for(
            "get_comments",
            project=project,
            site=site,
            memory=str(memory),
        )
    )
