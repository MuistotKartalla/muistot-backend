from time import time
from typing import Union

from databases import Database
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from .old_db import old_db as dbb
from .old_models import *
from ..database import Depends
from ..utils import *

router = APIRouter()

LANGUAGES: List[Union[List[str], float]] = [None, time()]


@router.get("/version", response_class=PlainTextResponse)
async def get_version():
    return PlainTextResponse(content="LATEST")


@router.get("/posts")
async def get_posts(r: Request, db: Database = Depends(dbb)):
    pass


@router.post("/posts")
async def add_posts(r: Request, db: Database = Depends(dbb)):
    pass


@router.get("/sites")
async def get_sites(r: Request, db: Database = Depends(dbb)):
    pass


@router.post("/sites")
async def add_sites(r: Request, db: Database = Depends(dbb)):
    pass


@router.get("/projects")
async def get_projects(r: Request, db: Database = Depends(dbb)):
    out = []
    async for res in db.iterate(
            """
            SELECT
                pk.Nimi as title,
                pk.Johdanto as description,
                pk.Kuvaus as contentDescription,
                p.visitorPosting,
                k.Tiedostonimi as image,
                p.PID as id,
                p.Alkaa,
                p.Loppuu,
                p.Poistuu
            FROM projektit p
                LEFT JOIN projektikuvaus pk ON pk.PID = p.PID
                    AND pk.LANG = :lang 
                LEFT JOIN Kuva k ON p.LogoKID = k.KID
            WHERE IFNULL(p.Poistuu > CURDATE(), TRUE)
            """,
            values=dict(lang=extract_language_or_default(r))
    ):
        p = Project(**res)
        p.moderators = [
            m[0] async for m in db.iterate(
                "SELECT UID FROM Moderators WHERE PID = :pid",
                values=dict(pid=p.id)
            )
        ]
        out.append(p)
    return out


@router.get("/projects/{project_id}")
async def get_project(project_id: int, r: Request, db: Database = Depends(dbb)):
    res = await db.fetch_one(
        """
        SELECT
            pk.Nimi as title,
            pk.Johdanto as description,
            pk.Kuvaus as contentDescription,
            p.visitorPosting,
            k.Tiedostonimi as image,
            p.PID as id,
            p.Alkaa,
            p.Loppuu,
            p.Poistuu
        FROM projektit p
            LEFT JOIN projektikuvaus pk ON pk.PID = p.PID
                AND pk.LANG = :lang 
            LEFT JOIN Kuva k ON p.LogoKID = k.KID
        WHERE IFNULL(p.Poistuu > CURDATE(), TRUE) AND p.PID = :pid
        """,
        values=dict(lang=extract_language_or_default(r), pid=project_id)
    )
    p = Project(**res)
    p.moderators = [
        m[0] async for m in db.iterate(
            "SELECT UID FROM Moderators WHERE PID = :pid",
            values=dict(pid=p.id)
        )
    ]
    return p


@router.get("/mementos")
async def get_mementos(r: Request, db: Database = Depends(dbb)):
    pass


@router.post("/mementos")
async def add_mementos(r: Request, db: Database = Depends(dbb)):
    pass
