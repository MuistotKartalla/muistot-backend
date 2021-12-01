from fastapi import APIRouter

from .old_interface import *
from ..database import dbb, Depends

router = APIRouter()


@router.get("/version")
async def get_version(db: Database = Depends(dbb)):
    pass


@router.get("/posts")
async def get_posts(db: Database = Depends(dbb)):
    pass


@router.post("/posts")
async def add_posts(db: Database = Depends(dbb)):
    pass


@router.get("/sites")
async def get_sites(db: Database = Depends(dbb)):
    load_sites()


@router.post("/sites")
async def add_sites(db: Database = Depends(dbb)):
    pass


@router.get("/projects")
async def get_projects(db: Database = Depends(dbb)):
    pass


@router.get("/project")
async def get_project(db: Database = Depends(dbb)):
    pass


@router.get("/mementos")
async def get_mementos(db: Database = Depends(dbb)):
    pass


@router.post("/mementos")
async def add_mementos(db: Database = Depends(dbb)):
    pass
