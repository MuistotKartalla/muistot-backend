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
    verify('bad-encoding', ":" * (hashes.MAX_BASE64_LENGTH - 9), no_encode=True)


def test_bad_checksum():
    token = decode(hashes.generate(10))
    verify('mismatch', token[:-1] + b':')


def test_bad_plain():
    token = decode(hashes.generate(10, payload=b'a'))
    verify('mismatch', token[:-hashes.CONTENT_LENGTH] + b':' + token[-hashes.CONTENT_LENGTH + 1:])


def test_bad_length_long():
    verify('bad-length', b'\x00' * (hashes.MAX_BASE64_LENGTH + 3), no_encode=True)


def test_bad_length_short():
    verify('bad-length', b'\x00' * (hashes.MIN_BASE64_LENGTH - 3), no_encode=True)


def test_bad_length_modulo():
    m = int((hashes.MAX_BASE64_LENGTH + hashes.MIN_BASE64_LENGTH) / 2)
    verify(
        'bad-modulo',
        b'\x00' * (m - 1 if m % 4 == 0 else m),
        no_encode=True
    )


def test_bad_length_decoded():
    verify('bad-token', 'A' * hashes.CONTENT_LENGTH)


def test_bad_time_expired():
    import time
    token = hashes.generate(1)
    time.sleep(2)
    verify('expired', token, no_encode=True)


def test_payload():
    import base64
    token = hashes.generate(10, hashes.int_to_payload(1234))
    decoded = base64.b64decode(token)
    assert int.from_bytes(
        decoded[-hashes.CONTENT_LENGTH:-hashes.HASH_LENGTH],
        byteorder='big',
        signed=False
    ) == 1234
    assert hashes.to_int(hashes.verify(token)) == 1234


def test_payload_2():
    import base64
    token = hashes.generate(10, b'hello world')
    decoded = base64.b64decode(token)
    assert decoded[-hashes.CONTENT_LENGTH:-hashes.HASH_LENGTH].rstrip(b'\x00') == b'hello world'
    assert hashes.verify(token) == b'hello world'


def test_too_long_payload():
    with raises(OverflowError):
        hashes.int_to_payload(int(2e128))
