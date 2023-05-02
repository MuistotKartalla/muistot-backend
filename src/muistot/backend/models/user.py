from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, validator

from ._fields import *
from .memory import Memory


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

    @validator("country")
    def validate_country(cls, value):
        if value is not None:
            import pycountry
            try:
                if len(value) == 2:
                    c = pycountry.countries.get(alpha_2=value)
                else:
                    c = pycountry.countries.get(alpha_3=value)
                return c.alpha_3
            except (LookupError, AttributeError):
                raise ValueError("Not a valid ISO3316 (2,3) country")
        else:
            return None


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

    class Config:
        __examples__ = {
            "partial": {
                "summary": "Change partial",
                "value": {
                    "country": "SE",
                    "birth_date": "2011-12-02",
                },
                "description": "Any amount of values can be added to the change request."
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
