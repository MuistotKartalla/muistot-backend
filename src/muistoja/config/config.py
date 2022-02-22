from typing import Dict, Optional, Set, Any

from pydantic import BaseModel, Field


class Database(BaseModel):
    host: str
    port: int
    database: str
    user: str
    password: str
    use_ssl: bool
    rollback: bool
    driver: str = "mysql"


class Mailer(BaseModel):
    name: str
    config: Any


class JWT(BaseModel):
    secret: str
    lifetime: int = 24 * 60 * 60 * 14
    algorithm: str = "HS256"
    reissue_threshold: int = 24 * 60 * 60


class Security(BaseModel):
    jwt: JWT
    bcrypt_cost: int = 12
    auto_publish: bool = False

    session_redis: str = "redis://session-storage?db=0"
    session_lifetime: int = 60 * 16
    session_token_bytes: int = 64

    oauth: Dict[str, Dict] = Field(default_factory=lambda: dict())


class FileStore(BaseModel):
    location: str = Field(regex="^.*/$")
    allow_anonymous: bool
    allowed_filetypes: Set[str]


class Localization(BaseModel):
    default: str
    supported: Set[str]


class BaseConfig(BaseModel):
    domain: Optional[str] = None
    testing: Optional[bool] = True
    db: Optional[Dict[str, Database]]

    localization: Optional[Localization]
    security: Optional[Security]
    files: Optional[FileStore]
    mailer: Optional[Mailer]
