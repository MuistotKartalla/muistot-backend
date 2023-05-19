from textwrap import dedent

from fastapi import Response, Depends
from fastapi.responses import JSONResponse

from .utils import make_router, d, require_auth
from .utils.common_responses import UNAUTHENTICATED, UNAUTHORIZED
from ..models import EmailStr, UID, UserData, PatchUser
from ..services.me import (
    get_user_data,
    update_personal_info,
    change_email,
    change_username,
)
from ...database import Database
from ...login.logic.session import start_session
from ...middleware import DatabaseMiddleware, SessionMiddleware
from ...security import scopes, SessionManager, User

router = make_router(tags=["Me"], default_response_class=Response)


@router.get(
    "/me",
    response_model=UserData,
    response_class=JSONResponse,
    responses={
        401: UNAUTHENTICATED,
        403: UNAUTHORIZED,
        422: d(
            dedent(
                """
                Invalid field values, e.g. Country has no ISO alpha 2 code.
                """
            )
        )
    },
)
@require_auth(scopes.AUTHENTICATED)
async def me(
        db: Database = Depends(DatabaseMiddleware.default),
        user: User = Depends(SessionMiddleware.user),
):
    return await get_user_data(db, user.identity)


@router.patch(
    "/me",
    status_code=204,
    responses={
        401: UNAUTHENTICATED,
        403: UNAUTHORIZED,
        422: d(
            dedent(
                """
                Invalid field values, e.g. Country has no ISO alpha 2 code.
                """
            )
        )
    },
)
@require_auth(scopes.AUTHENTICATED)
async def update_me(
        model: PatchUser,
        db: Database = Depends(DatabaseMiddleware.default),
        user: User = Depends(SessionMiddleware.user),
):
    await update_personal_info(db, user.identity, model)


@router.post(
    "/me/email",
    status_code=200,
    responses={
        401: UNAUTHENTICATED,
        403: UNAUTHORIZED,
        422: d(
            dedent(
                """
                Invalid value for email.
                """
            )
        )
    },
)
@require_auth(scopes.AUTHENTICATED)
async def change_my_email(
        email: EmailStr,
        db: Database = Depends(DatabaseMiddleware.default),
        user: User = Depends(SessionMiddleware.user),
        sm: SessionManager = Depends(SessionMiddleware.get),
):
    if await change_email(db, user.identity, email, sm):
        return await start_session(user.identity, db, sm)
    else:
        return Response(status_code=304)


@router.post(
    "/me/username",
    status_code=200,
    description="Changes username. If successful (204) the user is logged out of __ALL__ sessions.",
    responses={
        401: UNAUTHENTICATED,
        403: UNAUTHORIZED,
        422: d(
            dedent(
                """
                Invalid value for username.
                """
            )
        )
    },
)
@require_auth(scopes.AUTHENTICATED)
async def change_my_username(
        username: UID,
        db: Database = Depends(DatabaseMiddleware.default),
        user: User = Depends(SessionMiddleware.user),
        sm: SessionManager = Depends(SessionMiddleware.get),
):
    if await change_username(db, user.identity, username, sm):
        return await start_session(username, db, sm)
    else:
        return Response(status_code=304)


@router.delete(
    "/me",
    status_code=204,
    responses={
        401: UNAUTHENTICATED,
        403: UNAUTHORIZED,
    },
    description="Discards this session i.e. logs the user out."
)
@require_auth(scopes.AUTHENTICATED)
async def log_me_out(
        user: User = Depends(SessionMiddleware.user),
        sm: SessionManager = Depends(SessionMiddleware.get),
):
    sm.end_session(user.token)


@router.delete(
    "/me/sessions",
    status_code=204,
    responses={
        401: UNAUTHENTICATED,
        403: UNAUTHORIZED,
    },
    description="Logs the user out of __ALL__ sessions."
)
@require_auth(scopes.AUTHENTICATED)
async def log_me_out_all(
        user: User = Depends(SessionMiddleware.user),
        sm: SessionManager = Depends(SessionMiddleware.get),
):
    sm.clear_sessions(user.identity)
