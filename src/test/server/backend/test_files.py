from base64 import b64encode
from pathlib import Path

import pytest
from fastapi import HTTPException
from muistot.files.files import check_file, Files

EXPECTED_EMPTY = (None, None)
SAMPLE_IMAGE = Path(__file__).parent / "integration" / "sample_image.jpg"


class MockUser:
    is_authenticated = True
    identity = None


def test_invalid_encoding_unicode():
    assert check_file('öäåöäö') == EXPECTED_EMPTY


def test_invalid_encoding_base64():
    assert check_file('a=') == EXPECTED_EMPTY


def test_unexpected_error_does_not_raise():
    assert check_file(123) == EXPECTED_EMPTY


def test_disallowed_filetype():
    with open(Path(__file__), 'rb') as f:
        data = b64encode(f.read()).decode('ascii')
    assert check_file(data) == EXPECTED_EMPTY


def test_valid_path_with_suffix():
    assert Files.path("abcd-1234.jpg")


def test_valid_path_no_suffix():
    assert Files.path("abcd")


def test_path_too_short():
    with pytest.raises(ValueError):
        Files.path("")


def test_path_bad_characters():
    with pytest.raises(ValueError):
        Files.path("aaa/../../evil.jpg")


def test_path_bad_characters_newline():
    with pytest.raises(ValueError):
        Files.path("aaa\naaa/../../evil.jpg")


@pytest.mark.anyio
async def test_handle_disallowed_filetype():
    with open(Path(__file__), 'rb') as f:
        data = b64encode(f.read()).decode('ascii')

    files = Files(None, MockUser())
    with pytest.raises(HTTPException) as e:
        await files.handle(data)

    assert e.value.status_code == 400


@pytest.mark.anyio
async def test_handle_db_failure():
    class MockDB:
        async def fetch_one(self, *_, **__):
            return None

    with open(SAMPLE_IMAGE, 'rb') as f:
        data = b64encode(f.read()).decode('ascii')

    files = Files(MockDB(), MockUser())
    with pytest.raises(HTTPException) as e:
        await files.handle(data)

    assert e.value.status_code == 503


@pytest.mark.anyio
async def test_handle_non_auth_user_none():
    class MockNonAuthUser:
        is_authenticated = False

    assert await Files(None, MockNonAuthUser()).handle("") is None


@pytest.mark.anyio
async def test_handle_none_image():
    assert await Files(None, MockUser()).handle(None) is None


@pytest.mark.anyio
async def test_handle_ok_with_mime():
    class MockDB:
        async def fetch_one(self, *_, **__):
            return [1, "abcd"]

    files = Files(MockDB(), MockUser())

    path = "/tmp/test_file_abcd"

    def assertion(file_name):
        assert file_name == "abcd"
        return path

    files.path = assertion

    with open(SAMPLE_IMAGE, 'rb') as f:
        data = "data:image/jpg;base64," + b64encode(f.read()).decode('ascii')

    # Don't want to write anything to disk so this is like this
    assert await files.handle(data) == 1

    with open(path, 'rb') as f:
        data2 = "data:image/jpg;base64," + b64encode(f.read()).decode('ascii')

    assert data2 == data
