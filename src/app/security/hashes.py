import binascii
from base64 import standard_b64encode as to_base64, standard_b64decode as from_base64
from typing import Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.hmac import HMAC

from ..config import Config

SECRET_KEY = Config.security.csrf.encode('ascii')
HASHER = HMAC(SECRET_KEY, SHA256())


def validate(plaintext: str, checksum: str) -> bool:
    try:
        h = HASHER.copy()
        h.update(from_base64(plaintext))
        h.verify(from_base64(checksum))
        return True
    except (InvalidSignature, binascii.Error, UnicodeEncodeError):
        pass
    except Exception as e:  # pragma: no cover
        import logging
        logging.getLogger("uvicorn.error").warning("Exception", exc_info=e)
    return False


def get_timestamp() -> str:
    import time
    return f":{int(time.time())}"


def generate() -> Tuple[str, str]:
    """
    :return: Base64(PLAIN):TIME, Base64(HASH)
    """
    from os import urandom
    word: bytes = urandom(10)
    time: str = get_timestamp()
    h = HASHER.copy()
    h.update(word)
    h.update(time.encode('ascii'))
    return to_base64(word + time.encode('ascii')).decode('ascii') + time, to_base64(h.finalize()).decode('ascii')


__all__ = ['generate', 'validate']
