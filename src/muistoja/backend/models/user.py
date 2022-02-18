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
    project: PID = Field(description='Project the comment connects to')
    site: SID = Field(description='Site the comment connects to')
    memory: MID = Field(description='Memory the comment connects to')

    class Config:
        __examples__ = {
            "Basic": {
                'project': 'muistotkartalla',
                'site': 'sample-site',
                'memory': 1,
                **Comment.Config.__examples__['own']
            }
        }


class UserMemory(Memory):
    """
    Memory model for user specific listings
    """
    project: PID = Field(description='Project this memory connects to')
    site: SID = Field(description='Site this memory connects to')

    class Config:
        __examples__ = {
            "Basic": {
                'project': 'muistotkartalla',
                'site': 'sample-site',
                **Memory.Config.__examples__['own']
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
                "username": "user",
                "email": "email@example.com",
            },
            "ISO3166-02": {
                "username": "user",
                "email": "email@example.com",
                "first_name": "Hello",
                "last_name": "World",
                "country": "FI-01",
                "city": "Mariehamn",
                "birth_date": "2001-01-05",
                "modified_at": "2022-01-15"
            },
            "ISO3166-01": {
                "username": "user",
                "email": "email@example.com",
                "first_name": "Hello",
                "last_name": "World",
                "country": "FI",
                "city": "Mariehamn",
                "birth_date": "2001-01-05",
                "modified_at": "2022-01-15"
            },
            "partial": {
                "username": "user",
                "email": "email@example.com",
                "country": "SE",
                "city": "My Imaginary City",
                "modified_at": "2022-02-15"
            }
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
                "username": "updated"
            },
            "email": {
                "email": "new@example.com"
            },
            "both": {
                "username": "updated",
                "email": "new@example.com"
            },
            "full": {
                "username": "user",
                "email": "user@example.com",
                "first_name": "My",
                "last_name": "User",
                "country": "AZ",
                "city": "Example",
                "birth_date": "1900-08-30",
                "modified_at": "2022-01-15"
            },
            "partial": {
                "username": "user",
                "email": "email@example.com",
                "country": "SE",
                "city": "My Imaginary City"
            },
            "explicit-delete": {
                "country": None
            }
        }
