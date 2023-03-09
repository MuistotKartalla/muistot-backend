import pytest
from fastapi import FastAPI
from fastapi import status
from httpx import AsyncClient
from muistot.login import register_oauth_providers

from login_urls import OAUTH_BASE


@pytest.fixture
def oauth_name():
    yield "imaginary"


@pytest.fixture(autouse=True)
def configure_oauth(oauth_name):
    from muistot.config import Config
    data = dict(raise_on_init=False)
    Config.security.oauth[f".{oauth_name}"] = data
    yield data
    del Config.security.oauth[f".{oauth_name}"]


@pytest.fixture
async def client(configure_oauth):
    app = FastAPI()
    register_oauth_providers(app)
    async with AsyncClient(app=app, base_url="http://test") as c:
        c.app = app
        yield c


@pytest.mark.anyio
async def test_oauth_registration(client, configure_oauth, oauth_name):
    r = await client.get(OAUTH_BASE)
    assert r.status_code == status.HTTP_200_OK
    providers = r.json()["oauth_providers"]
    assert len(providers) != 0
    assert oauth_name in providers

    r = await client.get(f"{OAUTH_BASE}/test")
    assert r.status_code == status.HTTP_200_OK


@pytest.mark.anyio
async def test_registration_fail(caplog, configure_oauth, oauth_name):
    configure_oauth.update(raise_on_init=True)

    app = FastAPI()
    register_oauth_providers(app)
    client = AsyncClient(app=app, base_url="http://test")

    assert oauth_name in caplog.text

    r = await client.get(OAUTH_BASE)
    assert r.status_code == status.HTTP_200_OK
    providers = r.json()["oauth_providers"]
    assert oauth_name not in providers
