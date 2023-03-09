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


class OrderBase(BaseModel):
    type: Literal["site", "memory", "comment", "project"]
    parents: Optional[Dict[Literal["site", "memory", "project"], Union[SID, MID, PID]]]
    identifier: Union[PID, SID, MID, CID]

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
        elif type_ == "comment":  # pragma: no branch
            # This is exhaustive so marking no branch
            assert issubclass(CID, type(id_)), f"{BAD_TYPE} identifier"
            assert len(parents_) == 3, BAD_PARENTS_CNT
            assert "project" in parents_ and "site" in parents_ and "memory" in parents_, BAD_PARENTS
        if parents_ is not None:
            for k, t in [("project", PID), ("site", SID), ("memory", MID)]:
                if k in parents_:
                    assert issubclass(t, type(parents_[k])), f"{BAD_TYPE} {k}"
        else:
            values["parents"] = dict()
        return values


async def check_exists(
        order: OrderBase,
        username: str,
        db: Database,
        check_published: bool = True
):
    keys = dict(
        pid=order.identifier if order.type == "project" else order.parents.get("project", None),
        sid=order.identifier if order.type == "site" else order.parents.get("site", None),
        mid=order.identifier if order.type == "memory" else order.parents.get("memory", None),
        cid=order.identifier if order.type == "comment" else None,
        user=username,
    )

    m = await db.fetch_one(
        """
        SELECT
            NOT p.published AS project_not_published,
            
            ISNULL(s.id)    AS sid,
            NOT s.published AS site_not_published,
            
            ISNULL(m.id)    AS mid,
            NOT m.published AS memory_not_published,
            
            ISNULL(c.id)    AS cid,
            NOT c.published AS comment_not_published,
            
            NOT (
                ISNULL(pa.user_id) 
                AND 
                ISNULL(u_super.id)
            )               AS admin
        FROM projects p
            LEFT JOIN sites s ON p.id = s.project_id
                AND s.name = :sid
            LEFT JOIN memories m ON s.id = m.site_id
                AND m.id = :mid
            LEFT JOIN comments c ON m.id = c.memory_id
                AND c.id = :cid
            LEFT JOIN users u_super
                    JOIN superusers su ON su.user_id = u_super.id  
                ON u_super.username = :user
            LEFT JOIN project_admins pa
                    JOIN users u_admin ON u_admin.id = pa.user_id
                        AND u_admin.username = :user
                ON pa.project_id = p.id
        WHERE p.name = :pid
        """,
        values=keys
    )

    admin: bool = m["admin"] if m is not None else False

    if m is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found\nproject")
    if (order.parents.get("site", None) or order.type == "site") and m["sid"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found\nsite")
    if (order.parents.get("memory", None) or order.type == "memory") and m["mid"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found\nmemory")
    if order.type == "comment" and m["cid"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found\ncomment")

    if not admin:
        if (
                order.parents.get("project", None) or (check_published and order.type == "project")
        ) and m["project_not_published"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found\nproject")
        if (
                order.parents.get("site", None) or (check_published and order.type == "site")
        ) and m["site_not_published"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found\nsite")
        if (
                order.parents.get("memory", None) or (check_published and order.type == "memory")
        ) and m["memory_not_published"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found\nmemory")
        if check_published and order.type == "comment" and m["comment_not_published"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found\ncomment")


class PUPOrder(OrderBase):
    """
    Publish-UnPublish Order

    Setting entities in a project to a published or un-published state.
    """
    publish: bool = True

    class Config:
        __examples__ = {
            "publish": {
                "summary": "Publishing a site",
                "value": {
                    "type": "site",
                    "identifier": "my-awesome-site#1234",
                    "publish": True,
                    "parents": {
                        "project": "my-awesome-project",
                    }
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
                    "parents": {
                        "project": "my-awesome-project",
                        "site": "my-awesome-site#1234",
                    },
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
                    "parents": {
                        "project": "my-awesome-project",
                        "site": "my_site",
                        "memory": 34,
                    },
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
    await check_exists(order, r.user.identity, db, check_published=False)
    await db.execute(
        f"""
        UPDATE {TABLE_MAP[order.type]}
        SET published = {1 if order.publish else 0}
        WHERE {ID_MAP[order.type]} = :id AND published = {0 if order.publish else 1}
        """,
        values=dict(id=order.identifier),
    )
    if await db.fetch_val("SELECT ROW_COUNT()") == 1:
        resp.status_code = status.HTTP_204_NO_CONTENT
    else:
        resp.status_code = status.HTTP_304_NOT_MODIFIED


class ReportOrder(OrderBase):
    class Config:
        __examples__ = {
            "publish": {
                "summary": "Reporting a site",
                "value": {
                    "type": "site",
                    "identifier": "my-awesome-site#1234",
                    "parents": {
                        "project": "my-awesome-project",
                    }
                },
            },
        }


@router.post(
    "/report",
    description=dedent(
        """
        This is a catch all endpoint for reporting.
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
        403: d("Session token is invalid or user lacks privileges"),
    },
)
@require_auth(scopes.AUTHENTICATED)
async def report(
        r: Request,
        resp: Response,
        order: ReportOrder = sample(ReportOrder),
        db: Database = DEFAULT_DB
):
    if order.type == "project":
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)
    else:
        await check_exists(order, r.user.username, db)
        await db.execute(
            f"""
            INSERT IGNORE INTO audit_{TABLE_MAP[order.type]} ({order.type}_id, user_id)
            SELECT r.id, u.id
            FROM {TABLE_MAP[order.type]} r 
                JOIN users u ON u.username = :user 
            WHERE r.{ID_MAP[order.type]} = :id
            """,
            values=dict(id=order.identifier, user=r.user.identity),
        )
        if await db.fetch_val("SELECT ROW_COUNT()") == 1:
            resp.status_code = status.HTTP_204_NO_CONTENT
        else:
            resp.status_code = status.HTTP_304_NOT_MODIFIED
