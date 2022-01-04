import binascii
import math
from base64 import b64decode, b64encode
from time import time as current_time
from typing import Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.hmac import HMAC

from ..config import Config

SECRET_KEY = Config.security.csrf.encode('ascii')
HASHER = HMAC(SECRET_KEY, SHA256())
START = 1635717600  # 2021-11-01 00:00:00 seconds

HAS_PAYLOAD = b'\x01'
DUMMY_PAYLOAD = b'\x02'

PREFIX = 1
PAYLOAD_LENGTH = 32
MAX_TIME_LENGTH = 32
HASH_LENGTH = 32

CONTENT_LENGTH = HASH_LENGTH + PAYLOAD_LENGTH
MIN_TOKEN_LENGTH = 1 + HASH_LENGTH + PAYLOAD_LENGTH + PREFIX
MAX_TOKEN_LENGTH = HASH_LENGTH + PAYLOAD_LENGTH + MAX_TIME_LENGTH + PREFIX

MIN_BASE64_LENGTH = math.ceil(4 * (MIN_TOKEN_LENGTH / 3))
MIN_BASE64_LENGTH -= MIN_BASE64_LENGTH % 4 + 1

MAX_BASE64_LENGTH = math.ceil(4 * (MAX_TOKEN_LENGTH / 3))
MAX_BASE64_LENGTH += (4 - MAX_BASE64_LENGTH % 4) + 1


def validate(plaintext: bytes, checksum: bytes) -> bool:
    """Validates two hashes"""
    try:
        h = HASHER.copy()
        h.update(plaintext)
        h.verify(checksum)
        return True
    except InvalidSignature:
        pass
    except Exception as e:  # pragma: no cover
        import logging
        logging.getLogger("uvicorn.error").warning("Exception", exc_info=e)
    return False


def generate(lifetime: int, payload: bytes = None) -> str:
    """
    Generate a Token (HMAC, SHA256).

    Token contains the given payload and a verifier for it.
    The lifetime is checked on verification.

    :param lifetime: Seconds
    :param payload:  Bytes
    :return:         Token
    """
    from os import urandom
    hashpart = (HAS_PAYLOAD if payload is not None else DUMMY_PAYLOAD) + (int(current_time()) + lifetime).to_bytes(
        length=MAX_TIME_LENGTH,
        byteorder='big',
        signed=False
    ).lstrip(b'\x00') + (payload.ljust(PAYLOAD_LENGTH, b'\x00') if payload is not None else urandom(PAYLOAD_LENGTH))
    h = HASHER.copy()
    h.update(hashpart)
    return b64encode(hashpart + h.finalize()).decode('ascii')


def verify(token: str) -> Optional[bytes]:
    """
    Verifies a token and returns the enclosed payload if this token contains one.
    The padding zero bytes are stripped

    :param token:   Token to be verified
    :return:        Optional payload
    :raises:        ValueError on invalid token with short and descriptive message
    """
    if len(token) % 4 != 0:
        raise ValueError("bad-modulo")

    if not (MAX_BASE64_LENGTH > len(token) > MIN_BASE64_LENGTH):
        raise ValueError("bad-length")

    try:
        token = b64decode(token, validate=True)
    except (binascii.Error, UnicodeEncodeError, ValueError):
        raise ValueError("bad-encoding")

    if len(token) < MIN_TOKEN_LENGTH:
        raise ValueError("bad-token")

    prefix = token[:PREFIX]
    token = token[PREFIX:]

    time = token[:-CONTENT_LENGTH]
    expires_at = int.from_bytes(
        time,
        byteorder='big',
        signed=False
    )
    plain = token[-CONTENT_LENGTH:-HASH_LENGTH]
    check = token[-HASH_LENGTH:]

    if current_time() > expires_at:
        raise ValueError("expired")

    if not validate(prefix + time + plain, check):
        raise ValueError("mismatch")

    if prefix[0] == HAS_PAYLOAD[0]:
        return plain.rstrip(b'\x00')


def int_to_payload(i: int) -> bytes:
    """Int to Bytes"""
    return i.to_bytes(
        length=PAYLOAD_LENGTH,
        byteorder='big',
        signed=False
    )


def to_int(b: bytes) -> int:
    """Bytes to Int"""
    return int.from_bytes(
        b,
        byteorder='big',
        signed=False
    )


__all__ = ['generate', 'verify']
