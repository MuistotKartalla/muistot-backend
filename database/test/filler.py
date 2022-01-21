from typing import TypeVar
import random
from databases import Database
from databases.core import Connection
from passlib.pwd import genword


def gen() -> str:
    return genword(length=64, entropy=48, charset='hex')


db_instance: Database = Database(
    'mysql://root:test@127.0.0.1:5601/muistot',
    ssl=False,
    min_size=1,
    max_size=10,
    charset='utf8mb4'
)

T = TypeVar('T', Connection, Database)


async def make_user(db: T) -> int:
    name = gen()
    email = gen()
    password = None
    return await db.fetch_val(
        'INSERT INTO users (email, username, password_hash) VALUE (:email, :name, :password) RETURNING id',
        values={
            'email': email,
            'name': name,
            'password': password
        })


async def make_image(db: T, user: int) -> int:
    return await db.fetch_val(
        'INSERT INTO images (file_name, uploader_id) VALUE (UUID(), :user) RETURNING id',
        values={
            'user': user
        }
    )


async def make_comment(db: T, memory: int):
    uid = await make_user(db)
    title = f"test comment {gen()}"
    await db.execute(
        'INSERT INTO comments (memory_id, user_id, published, comment) VALUE (:memory, :user, 1, :comment)',
        values={
            'memory': memory,
            'user': uid,
            'comment': title,
        }
    )


top = 70.1, 19.4
low = 59.9, 33.3
diff_lat = top[0] - low[0]
diff_lon = top[1] - low[1]


async def make_memory(db: T, site: int):
    uid = await make_user(db)
    memory = await db.fetch_val(
        'INSERT INTO memories (site_id, user_id, published, story, title) '
        'VALUE (:site, :user, 1, :story, :title) '
        'RETURNING id',
        values={
            'user': uid,
            'site': site,
            'story': f'test story {gen()}',
            'title': f'test title {gen()}'
        }
    )
    for i in range(0, random.randint(1, 10)):
        await make_comment(db, memory)


async def make_site(db: T, project: int, admin: int):
    import random

    name = gen()

    lat = low[0] + diff_lat * random.random()
    lon = low[1] + diff_lon * random.random()

    site = await db.fetch_val(
        'INSERT INTO sites (name, project_id, modifier_id, location, published) '
        'VALUE (:name, :project, :admin, POINT(:lon, :lat), 1) RETURNING id',
        values={
            'name': name,
            'project': project,
            'admin': admin,
            'lat': lat,
            'lon': lon
        }
    )

    await db.execute(
        "INSERT INTO site_information (site_id, lang_id, name, abstract, description, modifier_id) "
        "VALUE (:site, 2, :name, :abstract, :desc, :modifier)",
        values={
            'site': site,
            'name': f"site {gen()}",
            'abstract': f"test site {gen()}",
            'desc': f"test description {gen()}",
            'modifier': admin
        }
    )

    print(f"project {project} site id {site} done")
    for i in range(0, random.randint(1, 10)):
        await make_memory(db, site)
    print(f"project {project} site id {site} comments done")


async def make_project(db: T):
    name = gen()
    admin = await make_user(db)
    image = await make_image(db, admin)
    project = await db.fetch_val(
        "INSERT INTO projects (name, modifier_id, published, image_id, default_language_id) "
        "VALUE (:name, :modifier_id, 1, :image, 2) RETURNING id",
        values={
            'name': name,
            'modifier_id': admin,
            'image': image,
        }
    )
    await db.execute(
        "INSERT INTO project_information (project_id, lang_id, name, abstract, description, modifier_id) "
        "VALUE (:project, 2, :name, :abstract, :desc, :modifier)",
        values={
            'project': project,
            'name': f"project {project}",
            'abstract': f"test project {project}",
            'desc': f"test description {project}",
            'modifier': admin
        }
    )
    await db.execute(
        'INSERT INTO project_admins (project_id, user_id) VALUE (:project, :user)',
        values={
            'project': project,
            'user': admin
        }
    )
    print(f"project {project} basics done")
    for i in range(0, random.randint(10, 50)):
        async with db.transaction():
            await make_site(db, project, admin)


async def run(i: int):
    print(f"starting project {i}")
    try:
        await make_project(db_instance)
    except BaseException as e:
        print(e)
    finally:
        print(f"project done {i}")


async def main():
    try:
        await db_instance.connect()
        print(f"Connected {await db_instance.fetch_val('SELECT 1')}")

        task_list = list()
        for i in range(0, 10):
            task_list.append(asyncio.create_task(run(i)))
        await asyncio.gather(*task_list)

    finally:
        await db_instance.disconnect()


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
