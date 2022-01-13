from .common_imports import *

router = make_router(tags=["Admin"])

ID_MAP = {
    'project': 'name',
    'site': 'name',
    'memory': 'id',
    'comment': 'id'
}

TABLE_MAP = {
    'project': 'projects',
    'site': 'sites',
    'memory': 'memories',
    'comment': 'comments'
}


@router.post('/projects/{project}/admin/publish')
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def publish(
        project: str,
        r: Request,
        object_type: Literal['site', 'memory', 'comment'],
        identifier: Union[str, int],
        set_published: bool,
        db: Database = Depends(dba)
):
    if not r.user.is_authenticated or not r.user.is_admin_in(project):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unauthorized')
    try:
        await db.execute(
            f"""
            UPDATE {TABLE_MAP[object_type]}
            SET published = {1 if set_published else 0}
            WHERE {ID_MAP[object_type]} = :id
            """,
            values=dict(id=identifier)
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Bad object type')
