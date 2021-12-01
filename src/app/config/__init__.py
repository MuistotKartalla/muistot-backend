import os
from os.path import expanduser
from typing import Dict, Optional

from pydantic import parse_file_as, BaseModel, HttpUrl


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


class Security(BaseModel):
    jwt: str
    csrf: str
    csrf_lifetime: int = 60
    bcrypt_cost: int = 12


class BaseConfig(BaseModel):
    testing: bool = True
    domain: Optional[str] = None
    db: Dict[str, Database] = {}
    mailer: Optional[Mailer] = None
    security: Security
    oauth: Dict[str, Dict] = {}


CONFIG_FILE = os.getenv('muistot-config') or expanduser("~/muistot-config.json")
try:
    Config = parse_file_as(BaseConfig, CONFIG_FILE)
except FileNotFoundError:
    Config = BaseConfig(
        db=dict(default=Database()),
        security=Security(
            jwt="test123",
            csrf="test123",
        )
    )

__all__ = ['Config']
