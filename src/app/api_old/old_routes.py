"""
The old API seemed to be something like this:

PROJECT
    - SITE
        - MEMORY

Also it has posts, but o idea what they are.
"""
from time import time
from typing import Union

from databases import Database
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from .old_db import old_db as dbb
from .old_models import *
from ..database import Depends
from ..security import require_auth, scopes
from ..utils import *

router = APIRouter(prefix='/old')

LANGUAGES: List[Union[List[str], float]] = [None, time()]


# DONE:
# TODO: sites, posts, mementos, project, projects

@router.get("/version", response_class=PlainTextResponse)
async def get_version() -> PlainTextResponse:
    return PlainTextResponse(content="LATEST")


@router.get("/projects")
async def get_projects(r: Request, db: Database = Depends(dbb), project=None) -> List[Project]:
    out = []
    async for res in db.iterate(
            f"""
            SELECT
                p.id,
                IFNULL(pi.name, p.name) AS title,
                pi.abstract AS description,
                pi.description AS contentDescription,
                p.anonymous_posting AS visitorPosting,
                i.file_name AS image,
                p.starts AS Alkaa,
                p.ends AS Loppuu,
                NULL AS Poistuu
            FROM projects p
                LEFT JOIN project_information pi ON p.id = pi.project_id
                JOIN languages l ON pi.lang_id = l.id
                LEFT JOIN images i ON i.id = p.image_id
            WHERE IFNULL(p.ends > CURDATE(), TRUE) 
                AND l.lang = :lang
            {"" if project is None else "   AND p.id = :project"}
            """,
            values={
                'lang': extract_language_or_default(r),
                **(dict() if project is None else dict(project=project))
            }
    ):
        p = Project(**res)
        p.moderators = [
            m[0] async for m in db.iterate(
                "SELECT user_id FROM project_admins WHERE project_id = :pid",
                values=dict(pid=p.id)
            )
        ]
        out.append(p)
    return out


@router.get("/projects/{project_id}")
async def get_project(project_id: int, r: Request, db: Database = Depends(dbb)) -> Project:
    return (await get_projects(r, db, project_id))[0]


@router.get("/sites")
async def get_sites(r: Request, db: Database = Depends(dbb)):
    pass


@router.post("/sites")
@require_auth(scopes.AUTHENTICATED)
async def add_sites(r: Request, db: Database = Depends(dbb)):
    pass


@router.get("/mementos")
async def get_mementos(r: Request, db: Database = Depends(dbb)):
    pass


@router.post("/mementos")
@require_auth(scopes.AUTHENTICATED)
async def add_mementos(r: Request, db: Database = Depends(dbb)):
    pass
