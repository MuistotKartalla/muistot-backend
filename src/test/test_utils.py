import pytest


@pytest.mark.parametrize("test_input", [
    'hello',
    'hello_world',
    'hello-world',
    '0_9',
    '1_09_hi-all'
])
def test_good(test_input: str):
    from app.utils import url_safe
    assert url_safe(test_input)


@pytest.mark.parametrize("test_input", [
    None,
    '',
    ' ',
    'hello world',
    'a/b',
    'd+e',
    '0+1',
    'a a a'
])
def test_bad(test_input: str):
    from app.utils import url_safe
    assert not url_safe(test_input)


@pytest.mark.parametrize("lang,expected", [
    ('fi', 'fi'),
    ('en', 'en'),
    ('not found', 'fi'),
    (None, 'fi')
])
def test_get_language(lang: str, expected: str):
    from test_csrf import MockRequest
    from app.headers import ACCEPT_LANGUAGE
    from app.utils import extract_language_or_default
    r = MockRequest()
    if lang is not None:
        r.headers[ACCEPT_LANGUAGE] = lang
    assert extract_language_or_default(r) == expected
