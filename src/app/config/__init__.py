from os.path import expanduser
from typing import Dict, Optional, List

from pydantic import parse_file_as, BaseModel, HttpUrl


class HttpsUrl(HttpUrl):
    allowed_schemes = {'https'}


class Database(BaseModel):
    host: str = "localhost"
    port: int = "5601"
    database: str = "muistot"
    user: str = "root"
    password: str = "test"
    use_ssl: bool = False
    rollback: bool = False


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
    lifetime: int = 60
    enabled: bool = False


class Security(BaseModel):
    jwt: JWT
    csrf: CSRF = CSRF(secret="not in use")
    bcrypt_cost: int = 12


class BaseConfig(BaseModel):
    testing: bool = True
    domain: Optional[str] = None
    db: Dict[str, Database] = {}
    mailer: Optional[Mailer] = None
    security: Security
    oauth: Dict[str, Dict] = {}
    languages: List[str]
    default_language = "fi"


CONFIG_FILE = expanduser('~/config.json')
try:
    Config = parse_file_as(BaseConfig, CONFIG_FILE)
except FileNotFoundError:
    try:
        CONFIG_FILE = './test_config.json'
        Config = parse_file_as(BaseConfig, CONFIG_FILE)
    except FileNotFoundError:
        raise RuntimeError(f"Failed to find config in {expanduser('~')} and .")

__all__ = ['Config']
