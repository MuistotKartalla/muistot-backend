from pathlib import Path
from typing import Dict, Set

from pydantic import BaseModel, Field, AnyUrl, AnyHttpUrl, Extra, DirectoryPath


class Database(BaseModel):
    # Basic config for url
    # --------------------
    host: str = "db"
    port: int = 3306
    database: str = "muistot"
    user: str = "root"
    password: str = "test"

    # Connection Config (databases)
    # -----------------------------
    # rollback: Force rollback
    # driver:   Driver to use for connection
    # -----------------------------
    rollback: bool = False
    driver: str = "mysql+asyncmy"
    driver_config: Dict = Field(default_factory=lambda: {
        "min_size": 4,
        "max_size": 30
    })

    # Custom Driver Options
    # -----------------------
    # workers:  Number of connection handler threads
    # cpw:      Number of connections per thread
    # max_wait: Seconds to wait for a free connection
    # ------------------------
    workers: int = 4
    cpw: int = 4
    max_wait: int = 2

    # Remote Database
    # -----------------------
    # ssl: Use ssl for database connection
    # -----------------------
    ssl: bool = False

    class Config:
        extra = Extra.ignore


class Mailer(BaseModel):
    driver: str = Field(".logmailer", regex=r'^\.?\w+(?:\.\w+)*$')
    config: Dict = Field(default_factory=dict)


class Namegen(BaseModel):
    url: AnyHttpUrl = "http://username-generator"


class Sessions(BaseModel):
    redis_url: AnyUrl = "redis://session-storage?db=0"
    token_lifetime: int = 60 * 16
    token_bytes: int = 32


class Security(BaseModel):
    bcrypt_cost: int = 12
    auto_publish: bool = False
    oauth: Dict[str, Dict] = Field(default_factory=dict)


class FileStore(BaseModel):
    location: DirectoryPath = Field(default_factory=lambda: Path("/opt/files"))
    allow_anonymous: bool = False
    allowed_filetypes: Set[str] = Field(default_factory=lambda: {
        "image/jpg",
        "image/jpeg",
        "image/png"
    })


class Localization(BaseModel):
    default: str = "fi"
    supported: Set[str] = Field(default_factory=lambda: {
        "fi",
        "en"
    })


class Cache(BaseModel):
    redis_url: AnyUrl = "redis://session-storage?db=1"
    cache_ttl: int = 60 * 10


class BaseConfig(BaseModel):
    testing: bool = Field(default_factory=lambda: True)
    database: Dict[str, Database] = Field(default_factory=lambda: dict(default=Database()))
    security: Security = Field(default_factory=Security)
    sessions: Sessions = Field(default_factory=Sessions)
    namegen: Namegen = Field(default_factory=Namegen)
    files: FileStore = Field(default_factory=FileStore)
    mailer: Mailer = Field(default_factory=Mailer)
    localization: Localization = Field(default_factory=Localization)
    cache: Cache = Field(default_factory=Cache)
