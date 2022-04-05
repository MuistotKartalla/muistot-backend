from ._imports import *
from .utils._responses import UNAUTHENTICATED, UNAUTHORIZED
from ..services.me import (
    get_user_data,
    update_personal_info,
    change_password,
    change_email,
    change_username,
    manager
)

router = make_router(tags=["Me"])


@router.get(
    "/me",
    response_model=UserData,
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
async def me(request: Request, db: Database = DEFAULT_DB):
    return await get_user_data(db, request.user.identity)


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
async def update_me(request: Request, model: PatchUser, db: Database = DEFAULT_DB):
    await update_personal_info(db, request.user.identity, model)


@router.put(
    "/me/password",
    status_code=200,
    response_class=Response,
    description="Changes password. The user is logged out of __ALL__ sessions."
)
@require_auth(scopes.AUTHENTICATED)
async def change_my_password(request: Request, password: str, db: Database = DEFAULT_DB):
    await change_password(db, request.user.identity, password, manager(request))


@router.post(
    "/me/email",
    status_code=204,
    response_class=Response,
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
async def change_my_email(request: Request, email: str, db: Database = DEFAULT_DB):
    if await change_email(db, request.user.identity, email):
        return Response(status_code=204)
    else:
        return Response(status_code=304)


@router.post(
    "/me/username",
    status_code=204,
    response_class=Response,
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
async def change_my_username(request: Request, username: str, db: Database = DEFAULT_DB):
    if await change_username(db, request.user.identity, username, manager(request)):
        return Response(status_code=204)
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
async def log_me_out(request: Request):
    manager(request).end_session(request.user.token)


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
async def log_me_out_all(request: Request):
    manager(request).clear_sessions(request.user.identity)
