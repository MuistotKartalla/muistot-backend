from pathlib import Path
from typing import Dict, Set

from pydantic import BaseModel, Field, AnyUrl, AnyHttpUrl, Extra, DirectoryPath


class Database(BaseModel):
    # Basic config for url
    # --------------------
    host: str
    port: int = 3306
    database: str = "muistot"

    # Authentication config
    # ---------------------
    user: str
    password: str

    # Connection Config (databases)
    # -----------------------------
    # rollback: Force rollback
    # driver:   Driver to use for connection
    # -----------------------------
    rollback: bool = False
    driver: str = "mysql+asyncmy"
    pool_size: int = 32
    pool_timeout_seconds: int = 10

    # Remote Database
    # -----------------------
    # ssl: Use ssl for database connection
    # -----------------------
    ssl: bool = False

    class Config:
        extra = Extra.ignore


class Mailer(BaseModel):
    driver: str = Field(default="LogMailer")
    config: Dict = Field(default_factory=dict)


class Namegen(BaseModel):
    url: AnyHttpUrl


class Sessions(BaseModel):
    redis_url: AnyUrl
    token_lifetime: int = 60 * 16
    token_bytes: int = 32


class FileStore(BaseModel):
    location: DirectoryPath = Field(default_factory=lambda: Path("/opt/files"))
    allowed_filetypes: Set[str] = Field(default_factory=lambda: {
        "image/jpg",
        "image/jpeg",
        "image/png"
    })

    class Config:
        extra = Extra.ignore


class Localization(BaseModel):
    default: str = "fi"
    supported: Set[str] = Field(default_factory=lambda: {
        "fi",
        "en"
    })


class Cache(BaseModel):
    redis_url: AnyUrl
    cache_ttl: int = 60 * 10


class BaseConfig(BaseModel):
    # Can be omitted
    testing: bool = Field(default_factory=lambda: True)
    files: FileStore = Field(default_factory=FileStore)
    mailer: Mailer = Field(default_factory=Mailer)
    localization: Localization = Field(default_factory=Localization)

    # Required
    sessions: Sessions = Field()
    database: Dict[str, Database] = Field()
    namegen: Namegen = Field()
    cache: Cache = Field()

    class Config:
        extra = Extra.ignore
