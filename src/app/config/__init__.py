from os.path import expanduser
from typing import Dict, Optional, Set

from pydantic import parse_file_as, BaseModel, HttpUrl, Field


class HttpsUrl(HttpUrl):
    allowed_schemes = {'https'}


class Database(BaseModel):
    host: str
    port: int = "3306"
    database: str
    user: str
    password: str
    use_ssl: bool = False
    rollback: bool = False
    driver: str = 'mysql'


class Mailer(BaseModel):
    key: str
    url: HttpsUrl
    port: int


class JWT(BaseModel):
    secret: str
    lifetime: int = 24 * 60 * 60 * 14
    algorithm: str = 'HS256'
    reissue_threshold: int = 24 * 60 * 60


class Security(BaseModel):
    jwt: JWT
    bcrypt_cost: int = 12


class FileStore(BaseModel):
    allowed_filetypes: Set[str] = {'jpeg', 'png'}  # https://docs.python.org/3/library/imghdr.html
    location: str = Field(regex='^.*/$', default='/opt/files/')
    allow_anonymous: bool = False


class BaseConfig(BaseModel):
    testing: bool = True
    auto_publish: bool = False

    default_language = "fi"
    languages: Set[str]

    security: Security
    domain: Optional[str] = None
    mailer: Optional[Mailer] = None
    db: Dict[str, Database] = {}
    oauth: Dict[str, Dict] = {}
    files: FileStore = FileStore()


CONFIG_FILE = expanduser('~/config.json')
try:
    Config: BaseConfig = parse_file_as(BaseConfig, CONFIG_FILE)
except FileNotFoundError:
    try:
        CONFIG_FILE = './test_config.json'
        Config: BaseConfig = parse_file_as(BaseConfig, CONFIG_FILE)
    except FileNotFoundError:
        raise RuntimeError(f"Failed to find config in {expanduser('~')} and .")

__all__ = ['Config']
