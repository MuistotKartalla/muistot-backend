import pytest
from httpx import AsyncClient

from muistot.backend import main
from muistot.backend.models import NewProject
from muistot.database import Databases
from muistot.login.logic.session import load_session_data
from muistot.sessions import Session
from utils import mock_request, genword, User


@pytest.fixture(scope="session")
async def client(db_instance):
    async def mock_dep():
        async with db_instance() as c:
            yield c

    main.app.dependency_overrides[Databases.default] = mock_dep

    async with AsyncClient(app=main.app, base_url="http://test") as client:
        client.app = main.app
        yield client
        client.app.state.SessionManager.redis.flushdb()


@pytest.fixture(scope="module")
def credentials():
    """collection of username, email
    """
    out = []
    usernames = set()
    while len(out) != 3:
        length = 12
        username = genword(length=length) + "#1234"
        if username not in usernames:
            email = f"{username}@example.com"
            out.append(User(username, email))
            usernames.add(username)
    yield out


@pytest.fixture(autouse=True, scope="module")
async def delete_users(db_instance, credentials):
    yield
    async with db_instance() as db:
        for username, _ in credentials:
            await db.execute("DELETE FROM users WHERE username = :un", values=dict(un=username))
            assert (
                       await db.fetch_val(
                           "SELECT EXISTS(SELECT * FROM users WHERE username = :un)",
                           values=dict(un=username)
                       )
                   ) == 0


@pytest.fixture(autouse=True, scope="module")
async def create_users(db_instance, credentials):
    async with db_instance() as db:
        for username, email in credentials:
            await db.execute(
                "INSERT INTO users (email, username, verified) "
                "VALUE (:email, :username, 1) ",
                values=dict(
                    username=username,
                    email=email,
                ),
            )


@pytest.fixture
def authenticate(client, db):
    async def authenticator(user: User):
        data = await load_session_data(user.username, db)
        session = Session(user.username, data)
        return {'Authorization': f"Bearer {client.app.state.SessionManager.start_session(session)}"}

    yield authenticator


@pytest.fixture
def login(credentials):
    yield User(*credentials[0])


@pytest.fixture
def username(login):
    yield login.username


@pytest.fixture
def repo_config(username):
    """Configure a repo from request with all privileges
    """
    yield mock_request(username)


@pytest.fixture
async def auth(client, credentials, authenticate):
    yield await authenticate(credentials[0])


@pytest.fixture
async def auth2(client, credentials, authenticate):
    yield await authenticate(credentials[1])


@pytest.fixture
async def auth3(client, credentials, authenticate):
    yield await authenticate(credentials[2])


@pytest.fixture
def image():
    import base64
    import pathlib
    with open(pathlib.Path(__file__).parent / "sample_image.jpg", "rb") as f:
        data = f.read()
    yield base64.b64encode(data).decode("ascii")


@pytest.fixture
async def auto_publish(db):
    """
    Tries to make projects auto publish in any scenario

    Modify all existing
      - Make published
      - Set Auto Publish to True
    Modify table
      - Set defaults to true for auto_publish and published
    Modify model
      - Set auto_publish to True

    But will not probably work in all cases
    """
    await db.execute("UPDATE projects SET auto_publish = TRUE, published = TRUE")
    await db.execute("ALTER TABLE projects MODIFY COLUMN auto_publish BOOLEAN NOT NULL DEFAULT TRUE")
    await db.execute("ALTER TABLE projects MODIFY COLUMN published BOOLEAN NOT NULL DEFAULT TRUE")

    f = NewProject.__fields__["auto_publish"]
    old = f.default

    f.default = True
    NewProject.__schema_cache__.clear()

    yield

    f.default = old
    NewProject.__schema_cache__.clear()

    await db.execute("ALTER TABLE projects MODIFY COLUMN auto_publish BOOLEAN NOT NULL DEFAULT FALSE")
    await db.execute("ALTER TABLE projects MODIFY COLUMN published BOOLEAN NOT NULL DEFAULT FALSE")


@pytest.fixture
async def superuser(db, client, login, authenticate):
    await db.execute(
        "INSERT INTO superusers (user_id) SELECT id FROM users WHERE username=:user",
        values=dict(user=login.username),
    )
    yield await authenticate(login)
    await db.execute(
        """
        DELETE su FROM superusers su JOIN users u ON u.id = su.user_id WHERE u.username = :user
        """,
        values=dict(user=login.username)
    )
