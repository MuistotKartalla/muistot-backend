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
                "summary": "simple",
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
                "value": {"username": "updated"},
            },
            "email": {"summary": "Change email", "value": {"email": "new@example.com"}},
            "both": {
                "summary": "Change username and email",
                "value": {"username": "updated", "email": "new@example.com"},
            },
            "full": {
                "summary": "Change everything",
                "value": {
                    "username": "user",
                    "email": "user@example.com",
                    "first_name": "My",
                    "last_name": "User",
                    "country": "AZ",
                    "city": "Example",
                    "birth_date": "1900-08-30",
                    "modified_at": "2022-01-15",
                },
            },
            "partial": {
                "summary": "Change partial",
                "value": {
                    "username": "user",
                    "email": "email@example.com",
                    "country": "SE",
                    "city": "My Imaginary City",
                },
            },
            "delete": {
                "summary": "Remove value",
                "value": {
                    "country": None,
                    "city": None,
                }
            },
        }
