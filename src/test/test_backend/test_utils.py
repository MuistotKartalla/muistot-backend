import pytest
from headers import ACCEPT_LANGUAGE, CONTENT_LANGUAGE
from muistoja.backend.repos.base.utils import extract_language
from starlette.authentication import UnauthenticatedUser


class MockRequest:
    def __init__(self):
        self.check_headers = {}
        self.headers = {}
        self.method = "POST"
        self.user = UnauthenticatedUser()


@pytest.mark.parametrize(
    "lang,expected",
    [
        ("fi", "fi"),
        ("en", "en"),
        ("en-US,en;q=0.5", "en"),
        ("az,bg,yf,en-US,en;q=0.5", "en"),
        ("az,bg,yf,fi-AA,en-US,en;q=0.5", "fi"),
        (None, "fi"),
        ("", "fi"),
    ],
)
def test_get_language(lang: str, expected: str):
    r = MockRequest()
    r.method = "GET"
    if lang is not None:
        r.headers[ACCEPT_LANGUAGE] = lang

    assert extract_language(r) == expected

    r = MockRequest()
    r.method = "POST"
    if lang is not None:
        r.headers[CONTENT_LANGUAGE] = lang

    assert extract_language(r) == expected


@pytest.mark.parametrize("lang", ["ax"])
def test_trow_language(lang: str):
    r = MockRequest()
    r.method = "GET"
    r.headers[ACCEPT_LANGUAGE] = lang

    with pytest.raises(ValueError):
        extract_language(r)

    r = MockRequest()
    r.method = "POST"
    r.headers[CONTENT_LANGUAGE] = lang

    with pytest.raises(ValueError):
        extract_language(r)