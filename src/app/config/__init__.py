import os
from os.path import expanduser
from typing import Dict, Optional, List

from pydantic import parse_file_as, BaseModel, HttpUrl

from . import scopes


class HttpsUrl(HttpUrl):
    allowed_schemes = {'https'}


class Database(BaseModel):
    host: str = "localhost"
    port: int = "3306"
    database: str = "muistot"
    user: str = "root"
    password: str = "test"


class Mailer(BaseModel):
    key: str
    url: HttpsUrl
    port: int


class JWT(BaseModel):
    secret: str
    lifetime: int = 24 * 60 * 60 * 14
    algorithm: str = 'HS256'
    reissue_threshold: int = 24 * 60 * 60


class CSRF(BaseModel):
    secret: str
    lifetime: str = 60


class Security(BaseModel):
    jwt: JWT
    csrf: CSRF
    bcrypt_cost: int = 12


class BaseConfig(BaseModel):
    testing: bool = True
    domain: Optional[str] = None
    db: Dict[str, Database] = {}
    mailer: Optional[Mailer] = None
    security: Security
    oauth: Dict[str, Dict] = {}
    languages: List[str]


CONFIG_FILE = os.getenv('muistot-config') or expanduser("~/muistot-config.json")
try:
    Config = parse_file_as(BaseConfig, CONFIG_FILE)
except FileNotFoundError:
    Config = BaseConfig(
        db=dict(default=Database()),
        security=Security(
            jwt=JWT(secret="test123"),
            csrf=CSRF(secret="test123"),
        ),
        languages=["fi", "en"]
    )

__all__ = ['Config', 'scopes']
