import binascii
from base64 import b64decode, b64encode
from time import time as current_time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.hmac import HMAC

from ..config import Config

SECRET_KEY = Config.security.csrf.encode('ascii')
HASHER = HMAC(SECRET_KEY, SHA256())
START = 1635717600  # 2021-11-01 00:00:00 seconds


def validate(plaintext: bytes, checksum: bytes) -> bool:
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


def generate(lifetime: int) -> str:
    from os import urandom
    hashpart = (int(current_time()) + lifetime).to_bytes(
        length=32,
        byteorder='big',
        signed=False
    ).lstrip(b'\x00') + urandom(14)
    h = HASHER.copy()
    h.update(hashpart)
    return b64encode(hashpart + h.finalize()).decode('ascii')


def verify(token: str):
    if not (105 > len(token) > 63 and len(token) % 4 == 0):
        raise ValueError("bad-length")

    try:
        token = b64decode(token, validate=True)
    except (binascii.Error, UnicodeEncodeError, ValueError):
        raise ValueError("bad-encoding")

    if len(token) < 47:
        raise ValueError("bad-token")

    time = token[:-46]
    expires_at = int.from_bytes(
        time,
        byteorder='big',
        signed=False
    )
    plain = token[-46:-32]
    check = token[-32:]

    if current_time() > expires_at:
        raise ValueError("expired")

    if not validate(time + plain, check):
        raise ValueError("mismatch")


__all__ = ['generate', 'verify']
