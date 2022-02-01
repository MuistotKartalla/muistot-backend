from datetime import datetime, timedelta
from typing import Dict, Optional

from jose import jwt as jose_jwt, JWTError

from ..config import Config


def generate_jwt(claims: Dict, *, lifetime: Optional[int] = None) -> str:
    """
    Generate a JWT

    :param claims:      Claims to sign
    :param lifetime:    Lifetime in seconds
    :return:            JWT
    """
    claims.update({
        'exp': datetime.utcnow() + timedelta(seconds=lifetime or Config.security.jwt.lifetime),
        'iat': datetime.utcnow()
    })
    return jose_jwt.encode(claims=claims, key=Config.security.jwt.secret, algorithm=Config.security.jwt.algorithm)


def read_jwt(jwt: str) -> Dict:
    """
    Reads values from a JWT

    :param jwt: Token
    :return:    Claims
    :raises:    ValueError on failure
    """
    try:
        return jose_jwt.decode(
            jwt,
            key=Config.security.jwt.secret,
            algorithms=Config.security.jwt.algorithm
        )
    except JWTError as e:
        raise ValueError("Invalid JWT", e)


__all__ = [
    'generate_jwt',
    'read_jwt'
]
