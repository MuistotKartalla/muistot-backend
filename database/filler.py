from typing import TypeVar

from databases import Database
from databases.core import Connection

db_instance: Database = Database(
    'mysql://root:test@localhost:6969/memories_on_a_map',
    ssl=False,
    min_size=20,
    max_size=20,
    charset='utf8mb4'
)

T = TypeVar('T', Connection, Database)


async def make_user(db: T) -> int:
    from passlib import pwd
    name = pwd.genword(entropy=64, charset='hex')
    email = pwd.genword(entropy=64, charset='hex')
    password = pwd.genword(entropy=64, charset='hex')
    return await db.fetch_val(
        'INSERT INTO users (email, username, password_hash) VALUE (:email, :name, :password) RETURNING id',
        values={
            'email': email,
            'name': name,
            'password': password
        })


async def make_image(db: T, user: int) -> int:
    from passlib import pwd
    name = pwd.genword(entropy=64, charset='hex')
    return await db.fetch_val(
        'INSERT INTO images (file_name, uploader_id) VALUE (:name, :user) RETURNING id',
        values={
            'name': name,
            'user': user
        }
    )


async def make_comment(db: T, site: int):
    uid = await make_user(db)
    title = f"test title"
    story = f"test story"
    await db.execute(
        'INSERT INTO comments (site_id, user_id, published, title, story) VALUE (:site, :user, 1, :title, :story)',
        values={
            'site': site,
            'user': uid,
            'title': title,
            'story': story
        }
    )


top = 70.1, 19.4
low = 59.9, 33.3
diff_lat = top[0] - low[0]
diff_lon = top[1] - low[1]


async def make_site(db: T, project: int, admin: int):
    import random
    from passlib import pwd

    name = pwd.genword(entropy=64, charset='hex')

    lat = low[0] + diff_lat * random.random()
    lon = low[1] + diff_lon * random.random()

    site = await db.fetch_val(
        'INSERT INTO sites (name, project_id, modifier_id, location) '
        'VALUE (:name, :project, :admin, POINT(:lon, :lat)) RETURNING id',
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
            'name': f"site {site}",
            'abstract': f"test site {site}",
            'desc': f"test description {site}",
            'modifier': admin
        }
    )

    print(f"project {project} site id {site} done")
    for i in range(0, 100):
        await make_comment(db, site)
    print(f"project {project} site id {site} comments done")


async def make_project(db: T):
    from passlib import pwd
    name = pwd.genword(entropy=64, charset='hex')
    admin = await make_user(db)
    image = await make_image(db, admin)
    project = await db.fetch_val(
        "INSERT INTO projects (name, modifier_id, published, image_id) "
        "VALUE (:name, :modifier_id, 1, :image) RETURNING id",
        values={
            'name': name,
            'modifier_id': admin,
            'image': image
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
    for i in range(0, 100):
        await make_site(db, project, admin)


async def run(i: int):
    print(f"starting project {i}")
    try:
        async with db_instance.connection() as conn:
            await make_project(conn)
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
