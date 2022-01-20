from passlib.context import CryptContext

from ..config import Config

crypto_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__default_rounds=Config.security.bcrypt_cost
)


def check_password(*, password_hash: str, password: str) -> bool:
    return crypto_context.verify(password, password_hash)


def hash_password(*, password: str) -> bytes:
    return crypto_context.hash(password)


__all__ = [
    'check_password',
    'hash_password'
]
