from databases import Database
from fastapi import APIRouter, Request

from ..database import dba, Depends
from ..utils import extract_language_or_default

router = APIRouter()


def get_projects(r: Request, db: Database = Depends(dba)):
    lang = extract_language_or_default(r)
