from passlib.context import CryptContext

from ..config import Config
from ..logging import log

crypto_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__default_rounds=Config.security.bcrypt_cost,
)


def check_password(*, password_hash: bytes, password: str) -> bool:
    try:
        return crypto_context.verify(password, password_hash)
    except Exception as e:
        log.warning("Failed password check with exception", exc_info=e)
        return False


def hash_password(*, password: str) -> bytes:
    return crypto_context.hash(password)


__all__ = ["check_password", "hash_password"]
