from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from ..database import dba, Depends, Database
from ..errors import Error
from ..headers import *
from ..security.users import LoginQuery, login_email, login_username, RegisterQuery, register_user

router = APIRouter()


@router.post("/login", tags=["Auth"])
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
    },
    tags=["Auth"]
)
async def default_register(request: Request, query: RegisterQuery, db: Database = Depends(dba)) -> JSONResponse:
    if AUTHORIZATION in request:
        return JSONResponse(status_code=409, content="Already signed-in")
    return await register_user(query, db)
