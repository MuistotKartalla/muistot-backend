from typing import Optional

from fastapi import HTTPException, status, Request

from ..models import PatchUser, UserData
from ...database import Database, IntegrityError
from ...sessions import SessionManager


async def check_username_not_exists(db: Database, username: Optional[str]):
    if username is not None:
        exists = await db.fetch_val(
            """
            SELECT EXISTS(SELECT 1 FROM users WHERE username = :user)
            """,
            values=dict(user=username),
        )
        if exists:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username in use")


async def change_email(db: Database, username: str, email: str, mgr: SessionManager) -> bool:
    try:
        m = await db.fetch_one(
            """
            SELECT EXISTS(SELECT 1 FROM users WHERE email = :email), 
                   (SELECT email=:email FROM users WHERE username = :user)
            """,
            values=dict(email=email, user=username)
        )
        if m[1]:
            return False
        elif m[0]:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email in use")
        mgr.clear_sessions(username)
        await db.execute(
            """
            UPDATE users SET email = :email WHERE username = :user
            """,
            values=dict(email=email, user=username)
        )
        mgr.clear_sessions(username)
        return True
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email in use")


async def change_username(db: Database, username_old: str, username_new: str, mgr: SessionManager) -> bool:
    if username_old != username_new:
        try:
            await check_username_not_exists(db, username_new)
            mgr.clear_sessions(username_old)
            mgr.clear_sessions(username_new)
            await db.execute(
                """
                UPDATE users SET username = :new WHERE username = :old
                """,
                values=dict(old=username_old, new=username_new)
            )
            return True
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username in use")
        finally:
            mgr.clear_sessions(username_old)
            mgr.clear_sessions(username_new)
    return False


async def update_personal_info(db: Database, username: str, model: PatchUser):
    data = model.dict(exclude_unset=True)
    keys = [*data.keys()]
    await db.execute(
        f"""
        INSERT INTO user_personal_data (user_id, {",".join(keys)})
        VALUES ((SELECT id FROM users WHERE username = :user), {",".join(f":{k}" for k in keys)})
        ON DUPLICATE KEY UPDATE {",".join(f"{k}=:{k}" for k in keys)}
        """,
        values={"user": username, **data}
    )


async def get_user_data(db: Database, username: str) -> UserData:
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
                    LEFT JOIN user_personal_data upd ON u.id = upd.user_id
                WHERE u.username = :user
                """,
                values=dict(user=username),
            )
        )
    )


def manager(r: Request) -> SessionManager:
    return r.state.manager
