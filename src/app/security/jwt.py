from calendar import timegm
from datetime import datetime, timedelta
from typing import Dict

from fastapi import FastAPI, Request
from jose import jwt as jose_jwt, JWTError

from ..config import Config
from ..headers import AUTHORIZATION


def generate_jwt(claims: Dict) -> str:
    """
    Generate a JWT

    :param claims:  Claims to sign
    :return:        JWT
    """
    claims.update({'exp': datetime.utcnow() + timedelta(seconds=Config.security.jwt.lifetime)})
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


def register_jwt_updater_middleware(app: FastAPI):  # pragma: no cover
    @app.middleware('http')
    async def jwt_middleware(request: Request, call_next):
        res = await call_next
        if AUTHORIZATION in request.headers:
            alg, jwt = request.headers[AUTHORIZATION].split()
            if alg == 'JWT':
                claims = read_jwt(jwt)
                now = timegm(datetime.utcnow().utctimetuple())
                exp = int(claims.pop("exp"))
                if exp < (now - Config.security.jwt.reissue_threshold):
                    res.headers[AUTHORIZATION] = generate_jwt(claims)
        return res


__all__ = [
    'generate_jwt',
    'read_jwt'
]
