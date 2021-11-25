import os
from os.path import expanduser
from typing import Dict

from pydantic import parse_file_as, BaseModel, HttpUrl


class HttpsUrl(HttpUrl):
    allowed_schemes = {'https'}


class Database(BaseModel):
    host: str
    port: int
    database: str
    user: str
    password: str


class Mailer(BaseModel):
    key: str
    url: HttpsUrl
    port: int


class Security(BaseModel):
    jwt: str
    csrf: str
    csrf_lifetime: int


class BaseConfig(BaseModel):
    testing: bool = True
    domain: str
    db: Database
    mailer: Mailer
    security: Security
    oauth: Dict[str, Dict] = {}


CONFIG_FILE = os.getenv('muistot-config') or expanduser("~/muistot-config.json")
try:
    Config = parse_file_as(BaseConfig, CONFIG_FILE)
except FileNotFoundError:
    Config = BaseConfig(
        domain="localhost",
        db=Database(
            host="localhost",
            port=3306,
            database="muistojakartalla",
            user="root",
            password="test"
        ),
        mailer=Mailer(
            key="test123",
            url="https://example.com",
            port=8080
        ),
        security=Security(
            jwt="test123",
            csrf="test123",
            csrf_lifetime=60
        )
    )

__all__ = ['Config']
