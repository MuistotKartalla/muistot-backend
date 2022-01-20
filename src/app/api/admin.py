from pydantic import BaseModel

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


class PUPOrder(BaseModel):
    """
    Publish-UnPublish Order

    Setting entities in a project to a published or un-published state.
    """
    type: Literal['site', 'memory', 'comment']
    identifier: Union[SID, MID, CID]
    publish: bool = True


@router.post(
    '/projects/{project}/admin/publish',
    description=(
            """
            This admin endpoint is for publishing entities.
            
            Type can be any child of Project.
            Identifier is its ID.
            """
    )
)
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def publish(
        r: Request,
        project: str,
        order: PUPOrder,
        db: Database = Depends(dba)
):
    if not r.user.is_admin_in(project):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unauthorized')
    try:
        if await db.fetch_val(
                f"""
            UPDATE {TABLE_MAP[order.type]}
            SET published = {1 if order.publish else 0}
            WHERE {ID_MAP[order.type]} = :id
            """,
                values=dict(id=order.identifier)
        ) == 1:
            return JSONResponse(204)
        else:
            return JSONResponse(status.HTTP_304_NOT_MODIFIED)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Bad object type')
