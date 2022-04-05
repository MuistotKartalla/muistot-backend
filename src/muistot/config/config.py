from typing import Dict, Optional, Set, Any

from pydantic import BaseModel, Field


class Database(BaseModel):
    host: str = "db"
    port: int = 3306
    database: str = "muistot"
    user: str = "root"
    password: str = "test"
    use_ssl: bool = False
    rollback: bool = False
    driver: str = "mysql"
    workers: int = 4
    cpw: int = 4
    max_wait: int = 2


class Mailer(BaseModel):
    name: str
    config: Any


class Security(BaseModel):
    bcrypt_cost: int = 12
    auto_publish: bool = False
    oauth: Dict[str, Dict] = Field(default_factory=dict)

    session_redis: str = "redis://session-storage?db=0"
    session_lifetime: int = 60 * 16
    session_token_bytes: int = 32  # Reasonable default

    namegen_url: str = "http://username-generator"


class FileStore(BaseModel):
    location: str = Field(regex="^.*/$", default="/opt/files")
    allow_anonymous: bool = Field(default=False)
    allowed_filetypes: Set[str] = Field(default_factory=lambda: {
        "image/jpg",
        "image/jpeg",
        "image/png"
    })


class Localization(BaseModel):
    default: str = "fi"
    supported: Set[str] = Field(default_factory=lambda: {
        "fi", "en", "se"
    })


class BaseConfig(BaseModel):
    testing: bool = Field(default=True)
    localization: Localization = Field(default_factory=Localization)
    security: Security = Field(default_factory=Security)
    files: FileStore = Field(default_factory=FileStore)

    db: Optional[Dict[str, Database]] = Field(default_factory=lambda: dict(default=Database()))
    mailer: Optional[Mailer] = Field(default=None)
