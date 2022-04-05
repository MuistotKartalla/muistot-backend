from fastapi import status
from headers import AUTHORIZATION

from urls import ENTRY
from utils import check_code


def test_bad_header_not_ascii(client):
    r = client.get(ENTRY, headers={AUTHORIZATION: "bearer dwaäödwädöwaädöaw"})
    check_code(status.HTTP_401_UNAUTHORIZED, r)


def test_bad_header_bad_base64_alts(client):
    r = client.get(ENTRY, headers={AUTHORIZATION: "bearer SGVsbG8gVGhlcmUg/w=="})
    check_code(status.HTTP_401_UNAUTHORIZED, r)


def test_bad_header_bad_base64_string(client):
    r = client.get(ENTRY, headers={AUTHORIZATION: "bearer aaaa"})
    check_code(status.HTTP_401_UNAUTHORIZED, r)


def test_non_valid_session(client):
    r = client.get(ENTRY, headers={AUTHORIZATION: "bearer YWJjZGVmZw=="})
    check_code(status.HTTP_401_UNAUTHORIZED, r)


def test_invalid_token_type(client):
    r = client.get(ENTRY, headers={AUTHORIZATION: "awdwadw YWJjZGVmZw=="})
    check_code(status.HTTP_401_UNAUTHORIZED, r)
