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
    assert csrf.CHECK in resp.headers


def test_request():
    plain_header, check_header = csrf.generate()
    r = MockRequest()
    r.headers[csrf.CHECK] = check_header
    r.headers[csrf.HEADER] = plain_header
    assert csrf.check_request(r) is None


def test_bad_request():
    _, check_header = csrf.generate()
    r = MockRequest()
    r.headers[csrf.CHECK] = check_header
    r.headers[csrf.HEADER] = "--"
    assert csrf.check_request(r) is not None


def test_bad_request_missing_value():
    _, check_header = csrf.generate()
    r = MockRequest()
    r.headers[csrf.CHECK] = check_header
    response = csrf.check_request(r)
    assert response is csrf.RESPONSES['missing-values']


def test_bad_request_mismatch():
    plain_header, check_header = csrf.generate()
    r = MockRequest()
    r.headers[csrf.CHECK] = check_header
    r.headers[csrf.HEADER] = plain_header[1:]
    response = csrf.check_request(r)
    assert response is csrf.RESPONSES['mismatch']


def test_bad_request_mismatch_2():
    plain_header, _ = csrf.generate()
    r = MockRequest()
    r.headers[csrf.CHECK] = "abc"
    r.headers[csrf.HEADER] = plain_header
    response = csrf.check_request(r)
    assert response is csrf.RESPONSES['mismatch']


def test_bad_request_method():
    r = MockRequest()
    r.method = "OPTIONS"
    response = csrf.check_request(r)
    assert response is csrf.RESPONSES['bad-method']


def test_bad_request_time():
    plain_header, check_header = csrf.generate()

    import base64
    p2 = base64.standard_b64decode(plain_header.split(':')[0])[:-1]
    p2 = base64.standard_b64encode(p2).decode('ascii')
    p2 = f"{p2}:{plain_header.split(':')[1]}"
    plain_header = p2

    r = MockRequest()
    r.headers[csrf.CHECK] = check_header
    r.headers[csrf.HEADER] = plain_header
    response = csrf.check_request(r)
    assert response is csrf.RESPONSES['mismatch']


def test_bad_request_expired():
    plain_header, check_header = csrf.generate()

    plain_header = plain_header.split(':')
    plain_header = f"{plain_header[0]}:{int(plain_header[1]) - csrf.EXPIRY - 1}"

    r = MockRequest()
    r.headers[csrf.CHECK] = check_header
    r.headers[csrf.HEADER] = plain_header
    response = csrf.check_request(r)
    assert response is csrf.RESPONSES['expired']


def test_bad_request_time_format():
    plain_header, check_header = csrf.generate()
    r = MockRequest()
    r.headers[csrf.CHECK] = check_header
    r.headers[csrf.HEADER] = plain_header + 'a'
    response = csrf.check_request(r)
    assert response is csrf.RESPONSES['bad-value']
