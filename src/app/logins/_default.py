from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from passlib.hash import bcrypt
from pydantic import BaseModel

from ..config import Config
from ..database import dba, Depends, Database
from ..errors import Error
from ..headers import *
from ..security import generate_jwt

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
    return bcrypt.verify(password, password_hash)


def hash_password(password: str) -> bytes:
    return bcrypt.using(rounds=Config.security.bcrypt_cost).hash(password)


def handle_hash(stored_hash: str, incoming_hash: str, username: str):
    if check_password(stored_hash, incoming_hash):
        return JSONResponse(status_code=200, headers={AUTHORIZATION: 'JWT ' + generate_jwt({
            'sub': username
        })})
    else:
        raise HTTPException(status_code=401, detail="Unauthorized")


def handle_login(m, login: LoginQuery) -> JSONResponse:
    if m is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    username: str = m[0]
    stored_hash: str = m[1]
    verified = m[2] == 1
    res = handle_hash(stored_hash, login.password, username)
    if not verified:
        raise HTTPException(status_code=401, detail="Not verified")
    else:
        return res


async def login_username(login: LoginQuery, db: Database) -> JSONResponse:
    return handle_login(
        await db.fetch_one(
            "SELECT username, password_hash, verified FROM users WHERE username=:uname",
            values=dict(uname=login.username)
        ),
        login
    )


async def login_email(login: LoginQuery, db: Database) -> JSONResponse:
    return handle_login(
        await db.fetch_one(
            "SELECT username, password_hash, verified FROM users WHERE email=:email",
            values=dict(email=login.email)
        ),
        login
    )


async def register_user(user: RegisterQuery, db: Database) -> JSONResponse:
    from ..mailer import get_mailer
    mailer = get_mailer()
    if not await mailer.verify_email(user.email):
        raise HTTPException(status_code=400, detail="Bad Email")
    m = await db.fetch_one(
        "SELECT"
        "   EXISTS(SELECT 1 FROM users WHERE username=:uname), "
        "   EXISTS(SELECT 1 FROM users WHERE email=:email)",
        values=dict(uname=user.username, email=user.email)
    )
    username_taken = m[0] == 1
    email_taken = m[1] == 1
    if username_taken:
        raise HTTPException(status_code=400, detail="Username already in use")
    elif email_taken:
        raise HTTPException(status_code=400, detail="Email already in use")
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
        raise HTTPException(status_code=400, detail="Email or username required")


@router.post(
    "/register",
    responses={
        '409': {
            'model': Error,
            "description": "User already exists or email/username is in use"
        }
    }
)
async def default_register(request: Request, query: RegisterQuery, db: Database = Depends(dba)) -> JSONResponse:
    if AUTHORIZATION in request:
        return JSONResponse(status_code=409, content="Already signed-in")
    return await register_user(query, db)
