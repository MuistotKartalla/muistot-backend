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
    ('en-US,en;q=0.5', 'en'),
    ('az,bg,yf,en-US,en;q=0.5', 'en'),
    ('az,bg,yf,fi-AA,en-US,en;q=0.5', 'fi'),
    (None, 'fi'),
    ('', 'fi'),
])
def test_get_language(lang: str, expected: str):
    from test_csrf import MockRequest
    from app.headers import ACCEPT_LANGUAGE, CONTENT_LANGUAGE
    from app.utils import extract_language

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


@pytest.mark.parametrize("lang", ['ax'])
def test_trow_language(lang: str):
    from test_csrf import MockRequest
    from app.headers import ACCEPT_LANGUAGE, CONTENT_LANGUAGE
    from app.utils import extract_language

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
