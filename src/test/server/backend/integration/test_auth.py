import pytest
from fastapi import status
from headers import AUTHORIZATION

from urls import ENTRY
from utils import check_code


@pytest.mark.anyio
async def test_bad_header_not_ascii(client):
    r = await client.get(ENTRY, headers={AUTHORIZATION: "bearer dwadwaddawdwdawdawaw"})
    check_code(status.HTTP_401_UNAUTHORIZED, r)


@pytest.mark.anyio
async def test_bad_header_bad_base64_alts(client):
    r = await client.get(ENTRY, headers={AUTHORIZATION: "bearer SGVsbG8gVGhlcmUg/w=="})
    check_code(status.HTTP_401_UNAUTHORIZED, r)


@pytest.mark.anyio
async def test_bad_header_bad_base64_string(client):
    r = await client.get(ENTRY, headers={AUTHORIZATION: "bearer aaaa"})
    check_code(status.HTTP_401_UNAUTHORIZED, r)


@pytest.mark.anyio
async def test_non_valid_session(client):
    r = await client.get(ENTRY, headers={AUTHORIZATION: "bearer YWJjZGVmZw=="})
    check_code(status.HTTP_401_UNAUTHORIZED, r)


@pytest.mark.anyio
async def test_invalid_token_type(client):
    r = await client.get(ENTRY, headers={AUTHORIZATION: "awdwadw YWJjZGVmZw=="})
    check_code(status.HTTP_401_UNAUTHORIZED, r)
