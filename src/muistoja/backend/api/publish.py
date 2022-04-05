from typing import Literal, Optional, Dict, Union

from fastapi import HTTPException, status
from pydantic import BaseModel, root_validator

from ._imports import *

router = make_router(tags=["Admin"])

BAD_PARENTS = "Bad parents"
BAD_PARENTS_CNT = "Incorrect parent count"
BAD_TYPE = "Wrong type for"

ID_MAP = {
    "project": "name",
    "site": "name",
    "memory": "id",
    "comment": "id"
}

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

    type: Literal["site", "memory", "comment", "project"]
    parents: Optional[Dict[Literal["site", "memory", "project"], Union[SID, MID, PID]]]
    identifier: Union[PID, SID, MID, CID]
    publish: bool = True

    @root_validator(skip_on_failure=True, pre=False)
    def validate_composition(cls, values):
        type_, parents_, id_ = values.get("type"), values.get("parents"), values.get("identifier")
        if type_ == "project":
            assert issubclass(PID, type(id_)), f"{BAD_TYPE} identifier"
            assert parents_ is None or len(parents_) == 0, BAD_PARENTS_CNT
        elif parents_ is None:
            assert False, BAD_PARENTS
        elif type_ == "site":
            assert issubclass(SID, type(id_)), f"{BAD_TYPE} identifier"
            assert len(parents_) == 1, BAD_PARENTS_CNT
            assert "project" in parents_, BAD_PARENTS
        elif type_ == "memory":
            assert issubclass(MID, type(id_)), f"{BAD_TYPE} identifier"
            assert len(parents_) == 2, BAD_PARENTS_CNT
            assert "project" in parents_ and "site" in parents_, BAD_PARENTS
        elif type_ == "comment":
            assert issubclass(CID, type(id_)), f"{BAD_TYPE} identifier"
            assert len(parents_) == 3, BAD_PARENTS_CNT
            assert "project" in parents_ and "site" in parents_ and "memory" in parents_, BAD_PARENTS
        if parents_ is not None:
            for k, t in [("project", PID), ("site", SID), ("memory", MID)]:
                if k in parents_:
                    assert issubclass(t, type(parents_[k])), f"{BAD_TYPE} {k}"
        return values

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
    "/admin/publish",
    description=dedent(
        """
        This admin endpoint is for publishing entities.
        
        This can be used to publish anything. 
        The PUPOrder validates any dependencies needed to resolve th entity e.g.
        
        ```
        PUPOrder[Comment]
        - ID: integer
        - Parents:
          - project: string
          - site:    string
          - memory:  integer
        ```
        """
    ),
    response_class=Response,
    status_code=204,
    responses={
        304: d("The resource wasn't changed"),
        204: d("Resource state changed successfully"),
        400: d("Parent or identifier validation failed"),
        404: d("Parents were not found"),
        422: d("Invalid entity"),
        403: d("The current user is not an admin for the selected project or session token is invalid"),
    },
)
@require_auth(scopes.AUTHENTICATED, scopes.ADMIN)
async def publish(
        r: Request,
        resp: Response,
        order: PUPOrder = sample(PUPOrder),
        db: Database = DEFAULT_DB,
):
    project = order.identifier if order.type == "project" else order.parents["project"]
    if not r.user.is_admin_in(project):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                    f"Unauthorized {r.user.identity}"
                    f"\nOrder: {project}"
                    + ''.join(map(lambda p: f'\nProject: {p}', r.user.admin_projects))
            ),
        )
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
