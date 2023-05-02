import os
import random

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncConnection

engine: AsyncEngine = create_async_engine("mysql+asyncmy://root:test@127.0.0.1:5601/muistot?charset=utf8mb4")

USERS = []
STATUS = []


def gen(length: int = 10) -> str:
    from passlib.pwd import genword

    return genword(length=length, entropy=48, charset="hex")


def genp(length: int) -> str:
    from passlib.pwd import genphrase

    return genphrase(length=length)


def print_status():
    data = [f"{i}-{p:.2f}%" for i, p in enumerate(STATUS)]
    print(f"Projects: {data}", end="\r")


async def make_user(db: AsyncConnection) -> int:
    _id = (await db.execute(
        text("INSERT INTO users (email, username, password_hash) VALUE (:email, :name, :password) RETURNING id"),
        {
            "email": f"{gen()}@example.com",
            "name": "".join(a[0].upper() + a[1:] for a in str(genp(2)).split())
                    + f"#{hex(int.from_bytes(os.urandom(3), byteorder='big', signed=False))}",
            "password": None,
        },
    )).fetchone()[0]
    await db.execute(
        text(
            """
            INSERT INTO user_personal_data (user_id, first_name, last_name, country, city, birth_date) 
            VALUE (:id, :first, :ln, :country, :city, DATE(CONCAT_WS('-', :y, :m, :d)))
            """
        ),
        {
            "id": _id,
            "first": gen(),
            "ln": gen(),
            "country": random.choice(["fi", "en", "swe"]),
            "city": gen(),
            "y": random.randint(1900, 2021),
            "m": random.randint(1, 12),
            "d": random.randint(1, 28),
        },
    )
    return _id


def get_user():
    return random.choice(USERS)


top = 70.1, 19.4
low = 59.9, 33.3
diff_lat = top[0] - low[0]
diff_lon = top[1] - low[1]


async def make_memory(db: AsyncConnection, site: int):
    uid = get_user()
    await db.execute(
        text(
            "INSERT INTO memories (site_id, user_id, published, story, title) "
            "VALUE (:site, :user, 1, :story, :title) "
            "RETURNING id"
        ),
        {
            "user": uid,
            "site": site,
            "story": f"test story {genp(200)}",
            "title": f"test title {gen()}",
        },
    )


async def make_site(db: AsyncConnection, project: int, admin: int):
    import random

    name = gen()

    lat = low[0] + diff_lat * random.random()
    lon = low[1] + diff_lon * random.random()

    site = (await db.execute(
        text(
            "INSERT INTO sites (name, project_id, modifier_id, location, published) "
            "VALUE (:name, :project, :admin, POINT(:lon, :lat), 1) RETURNING id"
        ),
        {
            "name": name,
            "project": project,
            "admin": admin,
            "lat": lat,
            "lon": lon,
        },
    )).fetchone()[0]

    await db.execute(
        text(
            "INSERT INTO site_information (site_id, lang_id, name, abstract, description, modifier_id) "
            "VALUE (:site, 2, :name, :abstract, :desc, :modifier)"
        ),
        {
            "site": site,
            "name": f"site {genp(3)} {gen()}",
            "abstract": f"test site {gen(100)}",
            "desc": f"test description {genp(1000)}",
            "modifier": admin,
        },
    )

    for i in range(0, random.randint(1, 25)):
        await make_memory(db, site)


async def make_project(i: int, db: AsyncConnection):
    name = gen()
    admin = get_user()
    project = (await db.execute(
        text(
            "INSERT INTO projects (name, modifier_id, published, image_id, default_language_id) "
            "VALUE (:name, :modifier_id, 1, :image, 2) RETURNING id"
        ),
        {
            "name": name,
            "modifier_id": admin,
            "image": None,
        },
    )).fetchone()[0]
    await db.execute(
        text(
            "INSERT INTO project_information (project_id, lang_id, name, abstract, description, modifier_id) "
            "VALUE (:project, 2, :name, :abstract, :desc, :modifier)"
        ),
        {
            "project": project,
            "name": f"project {project}",
            "abstract": f"test project {project}",
            "desc": f"test description {project}",
            "modifier": admin,
        },
    )
    await db.execute(
        text("INSERT INTO project_admins (project_id, user_id) VALUE (:project, :user)"),
        {"project": project, "user": admin},
    )
    print_status()
    _max = random.randint(10, 100)
    for j in range(0, _max):
        # async with db.transaction():
        await make_site(db, project, admin)

        STATUS[i] = (j + 1) / _max * 100
        print_status()


async def run(i: int):
    async with engine.begin() as c:
        await make_project(i, c)


async def main():
    try:
        async with engine.begin() as c:
            print(f"Connected {(await c.execute(text('SELECT 1'))).fetchone()[0]}")
            print("Creating users", end="\r")
            for j in range(0, 10_000):
                print(f"Creating users ({(j + 1) / 10_000 * 100:.2f}%)", end="\r")
                USERS.append(await make_user(c))
        print()
        print("Users done")
        task_list = list()
        for i in range(0, 10):
            STATUS.append(0)
            task_list.append(asyncio.create_task(run(i)))
        await asyncio.gather(*task_list)
    finally:
        print()
        print("Done")
        await engine.dispose()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
