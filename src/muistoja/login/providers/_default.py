from databases import Database
from fastapi import APIRouter, Request, HTTPException, Response, Depends
from fastapi.responses import JSONResponse
from headers import *

from ..logic.email import send_email
from ..logic.login import login_email, login_username, register_user, confirm
from ..logic.models import LoginQuery, RegisterQuery
from ...database import dba

router = APIRouter()


@router.post(
    "/login",
    tags=["Auth"],
    response_class=Response,
    status_code=200,
    responses={
        200: {"description": "Successful Login"},
        400: {"description": "Bad Request"},
    }
)
async def default_login(r: Request, login: LoginQuery, db: Database = Depends(dba)):
    if login.username is not None:
        return await login_username(login, db, r.state.manager)
    elif login.email is not None:
        return await login_email(login, db, r.state.manager)
    else:
        raise HTTPException(status_code=400)


@router.post(
    "/register",
    responses={
        201: {"description": "Successful user creation"},
        409: {"description": "User already exists or email/username is in use"},
        403: {"description": "User is already logged in"}
    },
    tags=["Auth"],
    response_class=Response,
    status_code=201,
)
async def default_register(r: Request, query: RegisterQuery, db: Database = Depends(dba)):
    if AUTHORIZATION in r.headers:
        return JSONResponse(status_code=403, content="Already signed-in")
    resp = await register_user(query, db)
    if resp.status_code == 201:
        await send_email(query.username, db)
    return resp


@router.post(
    "/register/confirm",
    tags=["Auth"],
    response_class=Response,
    status_code=204,
    responses={
        404: {"description": "Failed to find verifier"},
        204: {"description": "Successful verification"},
    },
)
async def register_confirm(user: str, token: str, db: Database = Depends(dba)):
    return await confirm(user, token, db)
