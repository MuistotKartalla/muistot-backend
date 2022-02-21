from typing import Literal, Optional, Dict, Union

from fastapi import HTTPException, status
from pydantic import BaseModel

from ._imports import *

router = make_router(tags=["Admin"])

ID_MAP = {"project": "name", "site": "name", "memory": "id", "comment": "id"}

TABLE_MAP = {
    "project": "projects",
    "site": "sites",
    "memory": "memories",
    "comment": "comments",
}


class PUPOrder(BaseModel):
    """
    Publish-UnPublish Order

    Setting entities in a project to a published or un-published state.
    """

    type: Literal["site", "memory", "comment"]
    parents: Optional[Dict[Literal["site", "memory"], Union[SID, MID]]]
    identifier: Union[SID, MID, CID]
    publish: bool = True

    class Config:
        __examples__ = {
            "publish": {
                "summary": "Publishing a site",
                "value": {
                    "type": "site",
                    "identifier": "my-awesome-site#1234",
                    "publish": True,
                },
            },
            "unpublish": {
                "summary": "Hiding a Memory",
                "description": dedent(
                    """
                    A Memory needs to supply its parents to be identified correctly.
                    
                    An error will be returned if the backend is not able to identify
                    the Memory if the parents are not present.
                    """
                ),
                "value": {
                    "type": "memory",
                    "parents": {"site": "my-awesome-site#1234"},
                    "identifier": 1234,
                    "publish": False,
                },
            },
            "comment": {
                "summary": "Publishing a Comment",
                "description": dedent(
                    """
                    A Comment needs to supply both parents.
                    
                    In case the backend is not able to recognize the comment an error is returned.
                    """
                ),
                "value": {
                    "type": "comment",
                    "parents": {"site": "my_site", "memory": 34},
                    "identifier": 1,
                    "publish": True,
                },
            },
        }


@router.post(
    "/projects/{project}/admin/publish",
    description=dedent(
        """
        This admin endpoint is for publishing entities.
        
        Type can be any child of Project.
        Identifier is its ID.
        """
    ),
    response_class=Response,
    status_code=204,
    responses={
        304: d("The resource wasn't changed"),
        204: d("Resource state changed successfully"),
        400: d("Parent or identifier validation failed"),
        404: d("Parents were not found"),
        403: d(
            "The current user is not an admin for the selected project or session token is invalid"
        ),
    },
)
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def publish(
        r: Request,
        resp: Response,
        project: str,
        order: PUPOrder = sample(PUPOrder),
        db: Database = DEFAULT_DB,
):
    if not r.user.is_admin_in(project):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized " + r.user.identity,
        )
    try:
        await db.execute(
            f"""
            UPDATE {TABLE_MAP[order.type]}
            SET published = {1 if order.publish else 0}
            WHERE {ID_MAP[order.type]} = :id
            """,
            values=dict(id=order.identifier),
        )
        if await db.fetch_val("SELECT ROW_COUNT()") == 1:
            resp.status_code = status.HTTP_204_NO_CONTENT
        else:
            resp.status_code = status.HTTP_304_NOT_MODIFIED
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Bad object type"
        )
