import pytest
from fastapi import status

from utils import check_code


@pytest.mark.anyio
async def test_hello(client):
    check_code(status.HTTP_200_OK, await client.get("/"))


@pytest.mark.anyio
async def test_projects(client):
    check_code(status.HTTP_200_OK, await client.get("/projects"))


@pytest.mark.anyio
async def test_image_redirect(client):
    check_code(status.HTTP_303_SEE_OTHER, await client.get("/images/a", follow_redirects=False))


@pytest.mark.anyio
async def test_lang(client):
    r = await client.get("/languages?q=fi")
    check_code(status.HTTP_200_OK, r)
    assert r.json() == {"id": "fin", "name": "Finnish", "alpha_2": "fi", "alpha_3": "fin"}


@pytest.mark.anyio
async def test_lang_no_short(client):
    r = await client.get("/languages?q=ace")
    check_code(status.HTTP_200_OK, r)
    assert r.json() == {"id": "ace", "name": "Achinese", "alpha_3": "ace"}


@pytest.mark.anyio
async def test_lang_not_found(client):
    r = await client.get("/languages?q=xxx")
    check_code(status.HTTP_404_NOT_FOUND, r)
