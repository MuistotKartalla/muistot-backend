from ..database import dbb, Database, Depends

from pydantic import BaseModel
from fastapi import APIRouter
from fastapi.security import HTTPBearer, HTTPBasicCredentials
from secrets import compare_digest

router = APIRouter()
auth = HTTPBearer(bearerFormat="JWT")


class Login(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(query: Login, db: Database = Depends(dbb)):
    # TODO : Hook to new login
    pass
