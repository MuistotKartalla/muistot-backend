from collections import namedtuple

import pytest
from fastapi.testclient import TestClient
from muistot.backend import main
from muistot.database import Databases
from muistot.security.password import hash_password

from utils import authenticate as auth, mock_request, genword

User = namedtuple('User', ('username', 'email', 'password'))


@pytest.fixture(scope="session")
def client(db_instance):
    async def mock_dep():
        async with db_instance() as c:
            yield c

    main.app.dependency_overrides[Databases.default] = mock_dep
    client = TestClient(main.app)

    class Mock:

        def __getattribute__(self, item):
            return lambda *_, **__: None

    client.app.state.FastStorage.redis = Mock()

    yield client


@pytest.fixture(scope="function")
def using_cache(client):
    old = client.app.state.FastStorage.redis
    client.app.state.FastStorage.redis = None
    client.app.state.FastStorage.connect()
    yield client.app.state.FastStorage.redis
    client.app.state.FastStorage.redis.flushdb()
    client.app.state.FastStorage.disconnect()
    client.app.state.FastStorage.redis = old


@pytest.fixture(scope="module")
def _credentials():
    """collection of username, email, password
    """
    out = []
    usernames = set()
    while len(out) != 3:
        length = 12
        username, password = genword(length=length) + "#1234", genword(length=length)
        if username not in usernames:
            email = f"{username}@example.com"
            out.append((username, email, password))
            usernames.add(username)
    yield out


@pytest.fixture(scope="module")
def users(_credentials):
    data = list()
    for c in _credentials:
        data.append(User(username=c[0], email=c[1], password=c[2]))
    yield data


@pytest.fixture(autouse=True, scope="module")
async def delete_users(db_instance, _credentials):
    yield
    async with db_instance() as db:
        for username, _, _ in _credentials:
            await db.execute("DELETE FROM users WHERE username = :un", values=dict(un=username))
            assert (
                       await db.fetch_val(
                           "SELECT EXISTS(SELECT * FROM users WHERE username = :un)",
                           values=dict(un=username)
                       )
                   ) == 0


@pytest.fixture(name="login", autouse=True, scope="module")
async def create_users(db_instance, _credentials):
    async with db_instance() as db:
        for username, email, password in _credentials:
            await db.execute(
                "INSERT INTO users (email, username, password_hash, verified) "
                "VALUE (:email, :username, :password, 1) ",
                values=dict(
                    password=hash_password(password=password), username=username, email=email
                ),
            )
    username, email, password = _credentials[0]
    yield username, email, password


@pytest.fixture(name="superuser")
async def superuser(db, client, login):
    await db.execute(
        "INSERT INTO superusers (user_id) SELECT id FROM users WHERE username=:user",
        values=dict(user=login[0]),
    )
    yield auth(client, login[0], login[2])
    await db.execute(
        """
        DELETE su FROM superusers su JOIN users u ON u.id = su.user_id WHERE u.username = :user
        """,
        values=dict(user=login[0])
    )


@pytest.fixture(name="auth")
def auth_fixture(client, _credentials):
    username, _, password = _credentials[0]
    yield auth(client, username, password)


@pytest.fixture(name="auth2")
def auth_fixture_2(client, _credentials):
    username, _, password = _credentials[1]
    yield auth(client, username, password)


@pytest.fixture(name="auth3")
def auth_fixture_3(client, _credentials):
    username, _, password = _credentials[2]
    yield auth(client, username, password)


@pytest.fixture(scope="module")
def repo_config(_credentials):
    yield mock_request(_credentials[0][0])


@pytest.fixture
def username(login):
    yield login[0]


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

    from muistot.backend.models import NewProject
    f = NewProject.__fields__["auto_publish"]
    old = f.default

    f.default = True
    NewProject.__schema_cache__.clear()

    yield

    f.default = old
    NewProject.__schema_cache__.clear()

    await db.execute("ALTER TABLE projects MODIFY COLUMN auto_publish BOOLEAN NOT NULL DEFAULT FALSE")
    await db.execute("ALTER TABLE projects MODIFY COLUMN published BOOLEAN NOT NULL DEFAULT FALSE")
