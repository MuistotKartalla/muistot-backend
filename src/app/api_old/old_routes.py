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

router = APIRouter(prefix='/old')

LANGUAGES: List[Union[List[str], float]] = [None, time()]


# DONE:
# TODO: sites, posts, mementos, project, projects

@router.get("/version", response_class=PlainTextResponse)
async def get_version() -> PlainTextResponse:
    return PlainTextResponse(content="LATEST")


@router.get("/projects")
async def get_projects(r: Request, db: Database = Depends(dbb), project=None) -> List[Project]:
    pass


@router.get("/projects/{project_id}")
async def get_project(project_id: int, r: Request, db: Database = Depends(dbb)) -> Project:
    pass


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
