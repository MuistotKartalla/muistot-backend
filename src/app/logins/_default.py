from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..database import dba, Depends, Database
from ..headers import *

router = APIRouter()


class LoginQuery(BaseModel):
    username: Optional[str]
    email: Optional[str]
    password: str


class RegisterQuery(BaseModel):
    username: str
    email: str
    password: str


def check_password(password_hash: str, password: str) -> bool:
    from passlib.hash import bcrypt
    return bcrypt.verify(password, password_hash)


def hash_password(password: str) -> bytes:
    from passlib.hash import bcrypt
    from ..config import Config
    return bcrypt.using(rounds=Config.security.bcrypt_cost).hash(password)


async def login_username(login: LoginQuery, db: Database) -> JSONResponse:
    stored_hash: str = await db.fetch_val(
        "SELECT EXISTS(SELECT password FROM users WHERE username=:uname)",
        values=dict(uname=login.username)
    )
    if check_password(stored_hash, login.password):
        pass
    else:
        pass


async def login_email(login: LoginQuery, db: Database) -> JSONResponse:
    pass


async def register_user(user: RegisterQuery, db: Database) -> JSONResponse:
    pass


@router.post("/login")
async def default_login(login: LoginQuery, db: Database = Depends(dba)) -> JSONResponse:
    if login.username is not None:
        return await login_username(login, db)
    elif login.email is not None:
        return await login_email(login, db)
    else:
        return JSONResponse(status_code=400, content={"error": {"message": "email or username required"}})


@router.post("/register")
async def default_register(request: Request, query: RegisterQuery, db: Database = Depends(dba)) -> JSONResponse:
    if AUTHORIZATION in request:
        return JSONResponse(status_code=401, content={"error": {"message": "already signed-in"}})
    return await register_user(query, db)
