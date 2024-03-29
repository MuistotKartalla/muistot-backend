"""
Supplies dependencies needed for session resolution.
"""
import base64
import binascii
import dataclasses
import json
import secrets
from hashlib import sha256
from typing import Optional, Dict, NoReturn, Union, List

from redis import Redis

ALT = b":-"
USER_PREFIX = "user:"
TOKEN_PREFIX = b"token:"


@dataclasses.dataclass
class Session:
    user: str
    data: Dict


def encode(token: bytes) -> str:
    return base64.b64encode(token, altchars=ALT).decode("ascii")


def decode(token: str) -> bytes:
    try:
        return sha256(base64.b64decode(token.encode("ascii"), altchars=ALT, validate=True)).digest()
    except (binascii.Error, UnicodeDecodeError):
        raise ValueError("Invalid Token Format")


class SessionManager:
    """Manages Session in Redis
    """

    redis: Redis

    def __init__(
            self,
            *,
            redis: Redis,
            token_bytes: int = 64,
            lifetime: Optional[int] = None,
    ):
        """Create a new SessionManager

        Parameters
        ----------
        redis
            Redis instance
        token_bytes
            Amount of bytes in token
        lifetime
            Session Token expiry time in seconds
        """
        super(SessionManager, self).__init__()
        self.bytes = token_bytes
        self.redis = redis
        self.lifetime = lifetime

    def extend(self, value: Union[bytes, str]):
        """Extends a key in the Redis

        Parameters
        ----------
        value
            Key to extend
        """
        if self.lifetime is not None:
            self.redis.expire(value, self.lifetime)

    def get_session(self, token: str) -> Session:
        """Fetches a session if one exists

        Parameters
        ----------
        token
            Session Token to fetch the session for

        Returns
        -------
        Session if one is available

        Raises
        ------
        ValueError
            On failure to resolve session
        """
        token = decode(token)
        self.extend(token)
        data = self.redis.get(token)
        if data is not None:
            return Session(**json.loads(data))
        raise ValueError("Invalid Session")

    def start_session(self, session: Session) -> str:
        """Returns a session id for given user and stores session data
        """
        self.clear_stale(session.user)
        while True:
            token = TOKEN_PREFIX + secrets.token_bytes(nbytes=self.bytes)
            token_hash = sha256(token).digest()
            if not self.redis.exists(token_hash):
                break
        self.redis.sadd(f"{USER_PREFIX}{session.user}", token_hash)
        self.redis.set(token_hash, json.dumps(dataclasses.asdict(session)), ex=self.lifetime)
        return encode(token)

    def end_session(self, token: str) -> NoReturn:
        """Ends a session

        Parameters
        ----------
        token
            Session token
        """
        token = decode(token)
        data = self.redis.get(token)
        self.redis.delete(token)
        if data is not None:
            self.redis.srem(f"{USER_PREFIX}{Session(**json.loads(data)).user}", token)

    def clear_sessions(self, user: str) -> NoReturn:
        """Clears all sessions for a user

        Parameters
        ----------
        user
            Username of user for which the sessions should be cleared
        """
        key = f"{USER_PREFIX}{user}"
        tokens = self.redis.smembers(key)
        self.redis.delete(key)
        for token in tokens:
            self.redis.delete(token)

    def clear_all_sessions(self) -> NoReturn:
        """Clears all sessions in the database
        """
        self.redis.flushdb()

    def clear_stale(self, user: str):
        """Clears all stale user sessions
        """
        user_sessions = f"{USER_PREFIX}{user}"
        for session in self.redis.smembers(user_sessions):
            if not self.redis.exists(session):
                self.redis.srem(user_sessions, session)

    def get_sessions(self, user: str) -> List[Session]:
        """Gets all open user sessions
        """
        self.clear_stale(user)
        out = list()
        for session in self.redis.smembers(f"{USER_PREFIX}{user}"):
            data = self.redis.get(session)
            if data:
                out.append(Session(**json.loads(data)))
        return out


__all__ = [
    "SessionManager",
    "Session",
]
