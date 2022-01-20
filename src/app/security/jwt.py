from datetime import datetime, timedelta
from typing import Dict

from jose import jwt as jose_jwt, JWTError

from ..config import Config


def generate_jwt(claims: Dict) -> str:
    """
    Generate a JWT

    :param claims:  Claims to sign
    :return:        JWT
    """
    claims.update({
        'exp': datetime.utcnow() + timedelta(seconds=Config.security.jwt.lifetime),
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
    except JWTError:
        raise ValueError("Invalid JWT")


__all__ = [
    'generate_jwt',
    'read_jwt'
]
