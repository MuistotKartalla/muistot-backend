import pytest
from fastapi import FastAPI
from fastapi import status
from fastapi.testclient import TestClient
from muistot.login import register_oauth_providers


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
def client(configure_oauth):
    app = FastAPI()
    register_oauth_providers(app)
    yield TestClient(app)


def test_oauth_registration(client, configure_oauth, oauth_name):
    r = client.get("/oauth")
    assert r.status_code == status.HTTP_200_OK
    providers = r.json()["oauth_providers"]
    assert len(providers) != 0
    assert oauth_name in providers

    r = client.get("/oauth/test")
    assert r.status_code == status.HTTP_200_OK


def registration_fail(caplog, configure_oauth, oauth_nam):
    configure_oauth.update(raise_on_init=True)

    app = FastAPI()
    register_oauth_providers(app)
    client = TestClient(app)

    assert oauth_name in caplog.text

    r = client.get("/oauth")
    assert r.status_code == status.HTTP_200_OK
    providers = r.json()["oauth_providers"]
    assert oauth_nam not in providers
