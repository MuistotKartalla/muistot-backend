import databases
import pytest
from fastapi.testclient import TestClient
from muistoja.backend import main
from muistoja.config import config_to_url
from muistoja.security.password import hash_password
from passlib.pwd import genword
from pymysql.err import OperationalError

from utils import authenticate as auth, mock_request


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def db(anyio_backend):
    from muistoja.config import Config
    db_instance = databases.Database(config_to_url(Config.db["default"]))
    while True:
        try:
            await db_instance.connect()
            break
        except OperationalError:
            pass
    try:
        yield db_instance
    finally:
        await db_instance.disconnect()


@pytest.fixture
def client(db):
    with TestClient(main.app) as instance:
        yield instance


@pytest.fixture(scope="module")
def _credentials():
    """collection of username, email, password
    """
    out = []
    usernames = set()
    while len(out) != 3:
        length = 12
        username, password = genword(length=length), genword(length=length)
        if username not in usernames:
            email = f"{username}@example.com"
            out.append((username, email, password))
            usernames.add(username)
    yield out


@pytest.fixture(autouse=True, scope="module")
async def delete_users(db: databases.Database, _credentials, anyio_backend):
    yield
    for username, _, _ in _credentials:
        await db.execute("DELETE FROM users WHERE username = :un", values=dict(un=username))
        assert (
                   await db.fetch_val(
                       "SELECT EXISTS(SELECT * FROM users WHERE username = :un)",
                       values=dict(un=username)
                   )
               ) == 0


@pytest.fixture(name="login", autouse=True, scope="module")
async def create_users(db: databases.Database, _credentials, anyio_backend):
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
async def superuser(db, client, login, anyio_backend):
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


@pytest.fixture
def repo_config(_credentials):
    yield mock_request(_credentials[0][0])


@pytest.fixture
def username(login):
    yield login[0]


@pytest.fixture
def image():
    import base64
    import pathlib
    with open(pathlib.Path(__file__).parent / "test_image.jpg", "rb") as f:
        data = f.read()
    yield base64.b64encode(data).decode("ascii")


@pytest.fixture
def auto_publish():
    from muistoja.config import Config
    pre = Config.security.auto_publish
    Config.security.auto_publish = True
    yield
    Config.security.auto_publish = pre
