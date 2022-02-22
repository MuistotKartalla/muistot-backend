from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from ._fields import *
from .comment import Comment
from .memory import Memory


class UserComment(Comment):
    """
    Comment model for user specific listings
    """

    project: PID = Field(description="Project the comment connects to")
    site: SID = Field(description="Site the comment connects to")
    memory: MID = Field(description="Memory the comment connects to")

    class Config:
        __examples__ = {
            "basic": {
                "summary": "Basic",
                "value": {
                    "project": "muistotkartalla",
                    "site": "sample-site",
                    "memory": 1,
                    **Comment.Config.__examples__["own"],
                },
                "description": "It is possible to query comments per user."
            }
        }


class UserMemory(Memory):
    """
    Memory model for user specific listings
    """

    project: PID = Field(description="Project this memory connects to")
    site: SID = Field(description="Site this memory connects to")

    class Config:
        __examples__ = {
            "basic": {
                "summary": "Basic",
                "value": {
                    "project": "muistotkartalla",
                    "site": "sample-site",
                    **Memory.Config.__examples__["own"],
                },
                "description": "It is possible to query submitted sites per user."
            }
        }


class _UserBase(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    country: Optional[COUNTRY] = COUNTRY_FIELD
    city: Optional[str]
    birth_date: Optional[date]


class UserData(_UserBase):
    """
    All user related data
    """

    username: UID
    email: EmailStr
    modified_at: Optional[datetime]

    class Config:
        __examples__ = {
            "simple": {
                "summary": "Simplest return type",
                "value": {
                    "username": "user",
                    "email": "email@example.com",
                },
            },
            "region": {
                "summary": "ISO3166-02",
                "value": {
                    "username": "user",
                    "email": "email@example.com",
                    "first_name": "Hello",
                    "last_name": "World",
                    "country": "FI-01",
                    "city": "Mariehamn",
                    "birth_date": "2001-01-05",
                    "modified_at": "2022-01-15",
                },
                "description": "The region format can be both v.1 or v.2 of ISO3166."
            },
            "country": {
                "summary": "ISO3166-01",
                "value": {
                    "username": "user",
                    "email": "email@example.com",
                    "first_name": "Hello",
                    "last_name": "World",
                    "country": "FI",
                    "city": "Mariehamn",
                    "birth_date": "2001-01-05",
                    "modified_at": "2022-01-15",
                },
                "description": "The region format can be both v.1 or v.2 of ISO3166."
            },
            "partial": {
                "summary": "Partial",
                "value": {
                    "username": "user",
                    "email": "email@example.com",
                    "country": "SE",
                    "city": "My Imaginary City",
                    "modified_at": "2022-02-15",
                },
                "description": "Any amount or combination of values can be returned. "
                               "Unset or null values are always absent."
            },
        }


class PatchUser(_UserBase):
    """
    Model for partial User Data update
    """

    username: Optional[UID]
    email: Optional[EmailStr]

    class Config:
        __examples__ = {
            "username": {
                "summary": "Change username",
                "value": {
                    "username": "updated"
                },
            },
            "email": {
                "summary": "Change email",
                "value": {
                    "email": "new@example.com"
                },
            },
            "both": {
                "summary": "Change username and email",
                "value": {
                    "username": "updated",
                    "email": "new@example.com"
                },
                "description": "It is possible to change both the username and email at once. "
                               "Both are checked for conflicts"
            },
            "partial": {
                "summary": "Change partial",
                "value": {
                    "username": "user",
                    "email": "email@example.com",
                    "country": "SE",
                    "birth_date": "2011-12-02",
                },
                "description": "Any amount of values can be added to the cahnge request."
            },
            "delete": {
                "summary": "Remove value",
                "value": {
                    "country": None,
                    "city": None,
                },
                "description": "Explicit _null_s delete existing values. "
                               "Leaving values empty does not change them."
            },
        }
