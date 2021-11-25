import json

from fastapi.responses import JSONResponse

from app.security import csrf


class MockRequest:

    def __init__(self):
        self.check_headers = {}
        self.headers = {}
        self.method = "POST"


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


def test_bad_request():
    r = MockRequest()
    r.headers[csrf.HEADER] = "--"
    response = csrf.check_request(r)
    assert response is not None, json.dumps(json.loads(response.body))


def test_bad_request_missing_value():
    r = MockRequest()
    response = csrf.check_request(r)
    assert response is csrf.RESPONSES['missing-value'], json.dumps(json.loads(response.body))


def test_bad_request_mismatch():
    from test_hashes import decode, encode
    token = decode(csrf.generate(10))
    r = MockRequest()
    r.headers[csrf.HEADER] = encode(token[:-1] + b':')
    response = csrf.check_request(r)
    assert response is csrf.RESPONSES['mismatch'], json.dumps(json.loads(response.body))


def test_bad_request_method():
    r = MockRequest()
    r.method = "OPTIONS"
    response = csrf.check_request(r)
    assert response is csrf.RESPONSES['bad-method'], json.dumps(json.loads(response.body))


def test_bad_request_expired():
    import time
    token = csrf.generate(1)
    time.sleep(2)
    r = MockRequest()
    r.headers[csrf.HEADER] = token
    response = csrf.check_request(r)
    assert response is csrf.RESPONSES['expired'], json.dumps(json.loads(response.body))


def test_bad_request_token_length():
    r = MockRequest()
    r.headers[csrf.HEADER] = 'a'
    response = csrf.check_request(r)
    assert response is csrf.RESPONSES['bad-length'], json.dumps(json.loads(response.body))


def test_bad_request_token_length_decoded():
    import base64
    r = MockRequest()
    r.headers[csrf.HEADER] = base64.b64encode(b'a' * 46)
    response = csrf.check_request(r)
    assert response is csrf.RESPONSES['bad-token'], json.dumps(json.loads(response.body))


def test_bad_request_token_encoding():
    r = MockRequest()
    r.headers[csrf.HEADER] = ':' * 64
    response = csrf.check_request(r)
    assert response is csrf.RESPONSES['bad-encoding'], json.dumps(json.loads(response.body))
