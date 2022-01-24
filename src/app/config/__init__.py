from os.path import expanduser
from typing import Dict, Optional, Set

from pydantic import parse_file_as, BaseModel, AnyHttpUrl, Field


class Database(BaseModel):
    host: str
    port: int
    database: str
    user: str
    password: str
    use_ssl: bool
    rollback: bool
    driver: str = 'mysql'


class Mailer(BaseModel):
    username: str
    password: str
    url: AnyHttpUrl
    port: int


class JWT(BaseModel):
    secret: str
    lifetime: int = 24 * 60 * 60 * 14
    algorithm: str = 'HS256'
    reissue_threshold: int = 24 * 60 * 60


class Security(BaseModel):
    jwt: JWT
    bcrypt_cost: int = 12
    auto_publish: bool = False
    oauth: Dict[str, Dict] = Field(default_factory=lambda: dict())


class FileStore(BaseModel):
    location: str = Field(regex='^.*/$')
    allow_anonymous: bool
    allowed_filetypes: Set[str]  # https://docs.python.org/3/library/imghdr.html


class Localization(BaseModel):
    default: str
    supported: Set[str]


class BaseConfig(BaseModel):
    domain: Optional[str] = None
    testing: bool = True
    db: Dict[str, Database]

    localization: Localization
    security: Security
    files: FileStore
    mailer: Optional[Mailer] = None


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
