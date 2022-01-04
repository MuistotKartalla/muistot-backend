import json

from fastapi.responses import JSONResponse
from starlette.authentication import UnauthenticatedUser, SimpleUser

from app.security.csrf import csrf
from app.security.csrf import hashes


class MockRequest:

    def __init__(self):
        self.check_headers = {}
        self.headers = {}
        self.method = "POST"
        self.user = UnauthenticatedUser()


def check(token, *checks):
    r = MockRequest()
    r.headers[csrf.HEADER] = token
    response = json.loads(csrf.check_request(r).body)
    for c in checks:
        assert c in response["error"]["details"]


def check2(r, *checks):
    response = json.loads(csrf.check_request(r).body)
    for c in checks:
        assert c in response["error"]["details"]


def test_response():
    resp = JSONResponse()
    csrf.set_csrf(resp)
    assert csrf.HEADER in resp.headers


def test_request():
    token = csrf.generate(10)
    r = MockRequest()
    r.headers[csrf.HEADER] = token
    response = csrf.check_request(r)
    assert response is None, json.dumps(json.loads(response.body))


def test_request_with_payload():
    token = csrf.generate(10, payload='test'.encode('utf-8'))
    r = MockRequest()
    r.headers[csrf.HEADER] = token
    r.user = SimpleUser('test')
    response = csrf.check_request(r)
    assert response is None, json.dumps(json.loads(response.body))


def test_request_with_bad_payload():
    token = csrf.generate(10, payload='test2'.encode('utf-8'))
    r = MockRequest()
    r.headers[csrf.HEADER] = token
    r.user = SimpleUser('test')
    check2(r, 'bad-payload')


def test_bad_request():
    r = MockRequest()
    r.headers[csrf.HEADER] = "--"
    response = csrf.check_request(r)
    assert response is not None, json.dumps(json.loads(response.body))


def test_bad_request_missing_value():
    check2(MockRequest(), 'missing-value')


def test_bad_request_mismatch():
    from test_hashes import decode, encode
    token = decode(csrf.generate(10))
    check(encode(token + b':'), 'mismatch')


def test_bad_request_mismatch_short():
    from test_hashes import decode, encode
    token = decode(csrf.generate(10))
    # This makes the token too short and expire
    check(encode(token[:-1]), 'expired')


def test_dupe():
    for i in range(0, 100_000):
        token = csrf.generate(10)
        assert csrf.generate(10) != token


def test_bad_request_method():
    r = MockRequest()
    r.method = "OPTIONS"
    check2(r, 'bad-method')


def test_bad_request_expired():
    import time
    token = csrf.generate(1)
    time.sleep(2)
    check(token, 'expired')


def test_bad_request_token_length():
    check('aaaa', 'bad-length')


def test_bad_request_token_modulo():
    check('a' * (hashes.MIN_TOKEN_LENGTH + 8), 'bad-modulo')


def test_bad_request_token_length_decoded():
    import base64
    check(base64.b64encode(b'a' * hashes.CONTENT_LENGTH), 'bad-token')


def test_bad_request_token_encoding():
    check(':' * (hashes.MIN_BASE64_LENGTH + 9), 'bad-encoding')
