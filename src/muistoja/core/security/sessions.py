"""
Supplies dependencies needed for session resolution.
"""
import base64
import binascii
import json
import os
from typing import Optional, Tuple, Dict

import aioredis
from fastapi import Request, status, FastAPI
from fastapi.security import HTTPBearer
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.authentication import AuthCredentials, AuthenticationMiddleware
from starlette.middleware.authentication import AuthenticationBackend, AuthenticationError
from starlette.requests import HTTPConnection

from .scopes import AUTHENTICATED
from .user import User
from ..config import Config
from ..errors import ErrorResponse, ApiError
from ..headers import AUTHORIZATION


def encode_token(user: str, token: bytes):
    return base64.b64encode(user.encode('utf-8') + token, altchars=b':-').decode('ascii')


def generate_token(user: str, token_bytes: int) -> Tuple[str, bytes]:
    """
    Generates a Config amount of bytes of random data prefixed with username

    :returns: encoded token, token bytes
    """
    token = os.urandom(token_bytes)
    return encode_token(user, token), token


def decode_token(encoded_token: str, token_bytes: int) -> Tuple[str, bytes]:
    """
    Decodes an encoded token

    :returns: username, token bytes
    """
    decoded = base64.b64decode(encoded_token, altchars=b':-', validate=True)
    return decoded[:-token_bytes].decode('utf-8'), decoded[-token_bytes:]


def on_error(_: Request, exc: AuthenticationError):
    """
    Customize the errors
    """
    message = exc.args[0] if len(exc.args) >= 1 else 'Error in auth'
    return ErrorResponse(error=ApiError(code=status.HTTP_403_FORBIDDEN, message=message))


class _BaseManager(HTTPBearer):

    def __init__(self):
        super(_BaseManager, self).__init__(
            bearerFormat='Verified Claims',
            description='Contains Username and Validity intervals with a verifier',
            auto_error=False
        )


class SessionManager(AuthenticationBackend):
    redis: aioredis.Redis

    def __init__(self, url: str, token_bytes: int):
        super(SessionManager, self).__init__()
        self.url = url
        self.token_bytes = token_bytes
        self.base = _BaseManager()
        self.connected = False

    async def connect(self):
        if not self.connected:
            self.redis = await aioredis.create_redis_pool(
                self.url,
                minsize=1,
                maxsize=10,
                encoding='utf-8'
            )
            self.connected = True

    async def authenticate(self, request: HTTPConnection) -> Optional[Tuple[AuthCredentials, User]]:
        header = request.headers.get(AUTHORIZATION, None)
        if header is not None:
            scheme, credentials = get_authorization_scheme_param(header)
            if scheme.lower() != 'bearer':
                raise AuthenticationError()
            try:
                user, token_bytes = decode_token(credentials, self.token_bytes)
                if await self._check(user, token_bytes):
                    user = User(username=user, token=token_bytes)
                    session_data = await self._fetch_session(credentials)
                    if 'projects' in session_data:
                        user.admin_projects = set(session_data['projects'])
                    creds = AuthCredentials(AUTHENTICATED)
                    request.scope['session'] = session_data
                    if 'scopes' in session_data:
                        creds.scopes.append(session_data['scopes'])
                        user.scopes.update(session_data['scopes'])
                else:
                    raise AuthenticationError('Invalid token')
            except (binascii.Error, IndexError, UnicodeDecodeError) as e:
                raise AuthenticationError('Invalid token')
        else:
            user = User()
            creds = AuthCredentials()
        request.state.manager = self
        return creds, user

    async def _fetch_session(self, encoded_token: str) -> Dict:
        await self.connect()
        out = await self.redis.get(encoded_token)
        if out is None:
            raise AuthenticationError('Expired')
        else:
            await self.redis.expire(encoded_token, Config.security.session_lifetime)
        out = json.loads(out)
        print(out)
        return out

    async def _check(self, user: str, token: bytes) -> Optional[str]:
        await self.connect()
        return await self.redis.sismember(user, token)

    async def start_session(self, user: str, data: Dict) -> str:
        """
        Returns a session header for a user
        """
        await self.connect()
        encoded, token = generate_token(user, self.token_bytes)
        await self.redis.sadd(user, token)
        await self.redis.set(
            encoded,
            json.dumps(data),
            expire=Config.security.session_lifetime
        )
        return encoded

    async def end_session(self, user: str, token: bytes):
        await self.connect()
        await self.redis.srem(user, token)
        await self.redis.delete(user.encode('utf-8') + token)

    async def clear_sessions(self, user: str):
        await self.connect()
        await self.redis.delete(user)

    async def clear_all_sessions(self):
        await self.connect()
        await self.redis.flushdb(async_op=True)


session_manager = SessionManager(Config.security.session_redis, Config.security.session_token_bytes)
"""
Simple but effective session manger added to all requests to supply user data.
"""


class _AuthManager(_BaseManager):

    def __init__(self):
        super(_AuthManager, self).__init__()

    async def __call__(self, request: Request):
        return request.user


auth = _AuthManager()
"""
Dumb manager that does nothing besides returning the user in current scope.

This is used to check if the user is authenticated.
"""


def add_session_manager(app: FastAPI):
    app.add_middleware(
        AuthenticationMiddleware,
        backend=SessionManager(Config.security.session_redis, Config.security.session_token_bytes),
        on_error=on_error
    )


__all__ = ["SessionManager", "auth", "session_manager", "add_session_manager"]
