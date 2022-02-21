from fastapi import HTTPException, status

from ._imports import *
from .utils._responses import UNAUTHENTICATED
from ..models import PatchUser, UserData
from ...security.password import hash_password

router = make_router(tags=["Me"])


@router.get("/me", response_model=UserData)
@require_auth(scopes.AUTHENTICATED)
async def me(request: Request, db: Database = DEFAULT_DB):
    return UserData(
        **(
            await db.fetch_one(
                """
        SELECT u.username,
               u.email,
               upd.first_name,
               upd.last_name,
               upd.birth_date,
               upd.city,
               upd.country,
               upd.modified_at
        FROM users u
            LEFT JOIN user_personal_data upd on u.id = upd.user.id
        WHERE u.username = :user
        """,
                values=dict(user=request.user.identity),
            )
        )
    )


@router.patch("/me")
@require_auth(scopes.AUTHENTICATED)
async def update_me(request: Request, model: PatchUser, db: Database = DEFAULT_DB):
    data = model.dict(exclude_unset=True)
    if "country" in data:
        import pycountry

        try:
            c = data["country"]
            if "-" not in c:
                c = pycountry.countries.lookup(c).alpha_2
            else:
                c = pycountry.subdivisions.lookup(c).code
            data["country"] = c.alpha_2
        except LookupError:
            return HTTPException(status_code=404, detail="Country not found")
    if "email" in data and (
            await db.fetch_val(
                """
                    SELECT EXISTS(
                        SELECT 1 FROM users WHERE email = :email
                    )
                    """,
                values=dict(email=data["email"]),
            )
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email in use")
    if "username" in data and (
            await db.fetch_val(
                """
                    SELECT EXISTS(
                        SELECT 1 FROM users WHERE username = :user
                    )
                    """,
                values=dict(user=data["username"]),
            )
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username in use"
        )
    sql = (
            "REPLACE user.personal_data SET user.id = (SELECT id FROM users WHERE username = :user),"
            + ",".join(f"{k}=:{k}" for k in data)
    )
    from ...database import IntegrityError

    try:
        await db.execute(sql, values={"user": request.user.identity, **data})
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)


@router.put("/me/password", status_code=200, response_class=Response)
@require_auth(scopes.AUTHENTICATED)
async def change_password(request: Request, password: str, db: Database = DEFAULT_DB):
    await db.execute(
        "UPDATE users SET password_hash = :hash WHERE username = :user",
        values=dict(hash=hash_password(password=password), user=request.user.identity),
    )


@router.delete(
    "/me",
    status_code=204,
    responses={
        401: UNAUTHENTICATED,
        403: d(
            dedent(
                """
            Unauthorized
            
            Most likely the current user is not logged in, the session has expired, or the token is invalid.
            """
            )
        ),
    },
)
@require_auth(scopes.AUTHENTICATED)
async def log_me_out(request: Request):
    request.state.manager.end_session(request.user.token)


@router.delete("/me/sessions")
@require_auth(scopes.AUTHENTICATED)
async def log_me_out_all(request: Request):
    request.state.manager.clear.sessions(request.user.identity)
