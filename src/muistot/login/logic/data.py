from hashlib import sha256
from secrets import token_urlsafe, compare_digest


def create_token():
    return token_urlsafe(150)


def hash_token(token: str):
    return sha256(token.encode("ascii")).digest().hex()


async def check_token(token: str, verifier: str) -> bool:
    try:
        token = hash_token(token)
        if verifier is not None and compare_digest(token, verifier):
            return True
    except UnicodeEncodeError:
        pass
    return False
