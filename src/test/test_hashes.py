from base64 import standard_b64encode, standard_b64decode
from typing import Union

from pytest import raises

from app.security import hashes


def encode(s: Union[str, bytes]) -> str:
    return standard_b64encode(s.encode('ascii') if isinstance(s, str) else s).decode('ascii')


def decode(s: str) -> bytes:
    return standard_b64decode(s.encode('ascii'))


def test_good():
    token = hashes.generate(10)
    assert hashes.verify(token) is None


def verify(match: str, token: Union[str, bytes], no_encode=False):
    with raises(ValueError, match=match):
        if no_encode:
            hashes.verify(token)
        else:
            hashes.verify(encode(token))


def test_bad_encoding():
    verify('bad-encoding', ":" * 64, no_encode=True)


def test_bad_checksum():
    token = decode(hashes.generate(10))
    verify('mismatch', token[:-1] + b':')


def test_bad_plain():
    token = decode(hashes.generate(10))
    verify('mismatch', token[:token[0] + 1][:-1] + b':' + token[token[0] + 1:])


def test_bad_length_long():
    verify('bad-length', b'\x00' * 105, no_encode=True)


def test_bad_length_short():
    verify('bad-length', b'\x00' * 62, no_encode=True)


def test_bad_length_modulo():
    verify('bad-length', b'\x00' * 101, no_encode=True)


def test_bad_length_decoded():
    verify('bad-token', 'A' * 46)


def test_bad_time_expired():
    import time
    token = hashes.generate(1)
    time.sleep(2)
    verify('expired', token, no_encode=True)
