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


def handle_hash(stored_hash: str, incoming_hash: str, username: str):
    from ..security.hashes import generate
    from ..config import Config
    if check_password(stored_hash, incoming_hash):
        # TODO: Not like this, actually use JWT
        return JSONResponse(status_code=200, headers={AUTHORIZATION: generate(
            Config.security.jwt_lifetime,
            username.encode('utf-8')
        )})
    else:
        return JSONResponse(status_code=401)


async def login_username(login: LoginQuery, db: Database) -> JSONResponse:
    m = await db.fetch_one(
        "SELECT username, password_hash FROM users WHERE username=:uname AND verified",
        values=dict(uname=login.username)
    )
    stored_hash: str = m[1]
    username: str = m[0]
    return handle_hash(stored_hash, login.password, username)


async def login_email(login: LoginQuery, db: Database) -> JSONResponse:
    m = await db.fetch_one(
        "SELECT username, password_hash FROM users WHERE email=:email AND verified",
        values=dict(email=login.email)
    )
    stored_hash: str = m[1]
    username: str = m[0]
    return handle_hash(stored_hash, login.password, username)


async def register_user(user: RegisterQuery, db: Database) -> JSONResponse:
    from ..mailer import get_mailer
    mailer = get_mailer()
    if not await mailer.verify_email(user.email):
        return JSONResponse(status_code=400, content={"error": {"message": "bad email"}})
    m = await db.fetch_one(
        "SELECT"
        "   EXISTS(SELECT 1 FROM users WHERE username=:uname), "
        "   EXISTS(SELECT 1 FROM users WHERE email=:email)",
        values=dict(uname=user.username, email=user.email)
    )
    username_taken = m[0] == 1
    email_taken = m[1] == 1
    if username_taken:
        return JSONResponse(status_code=400, content={"error": {"message": "username taken"}})
    elif email_taken:
        return JSONResponse(status_code=400, content={"error": {"message": "email already in use"}})
    else:
        await db.execute(
            "INSERT INTO users (email, username, password_hash) VALUE (:email, :user, :password)",
            values=dict(email=user.email, user=user.username, password=hash_password(user.password))
        )
        await mailer.send_verify_email(user.username, user.email)
        return JSONResponse(status_code=201)


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
