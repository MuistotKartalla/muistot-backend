from fastapi import APIRouter, Request, Response, Depends

from ..logic.login import register_user, confirm, password_login
from ..logic.models import LoginQuery, RegisterQuery
from ...database import Database, Databases
from ...security import disallow_auth

router = APIRouter()


@router.post(
    "/password",
    tags=["Auth"],
    response_class=Response,
    status_code=200,
    responses={
        200: {"description": "Successful Login"},
        400: {"description": "Bad Request"},
        403: {"description": "Already logged in"},
    }
)
@disallow_auth
async def default_login(r: Request, login: LoginQuery, db: Database = Depends(Databases.default)):
    return await password_login(login, db, r.state.manager)


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
@disallow_auth
async def default_register(query: RegisterQuery, db: Database = Depends(Databases.default)):
    return await register_user(query, db)


@router.post(
    "/confirm",
    tags=["Auth"],
    response_class=Response,
    status_code=200,
    responses={
        404: {"description": "Failed to find verifier"},
        403: {"description": "Already logged in"},
        200: {"description": "Successful verification"},
    },
)
@disallow_auth
async def register_confirm(r: Request, user: str, token: str, db: Database = Depends(Databases.default)):
    return await confirm(user, token, db, r.state.manager)
