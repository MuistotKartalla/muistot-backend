from fastapi import status

from utils import check_code


def test_hello(client):
    check_code(status.HTTP_200_OK, client.get("/"))


def test_projects(client):
    check_code(status.HTTP_200_OK, client.get("/projects"))


def test_image_redirect(client):
    check_code(status.HTTP_303_SEE_OTHER, client.get("/images/a", allow_redirects=False))


def test_lang(client):
    r = client.get("/languages?q=fi")
    check_code(status.HTTP_200_OK, r)
    assert r.json() == {"id": "fin", "name": "Finnish", "alpha_2": "fi", "alpha_3": "fin"}


def test_lang_no_short(client):
    r = client.get("/languages?q=ace")
    check_code(status.HTTP_200_OK, r)
    assert r.json() == {"id": "ace", "name": "Achinese", "alpha_3": "ace"}


def test_lang_not_found(client):
    r = client.get("/languages?q=xxx")
    check_code(status.HTTP_404_NOT_FOUND, r)
