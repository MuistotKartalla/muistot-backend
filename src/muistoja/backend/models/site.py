from typing import Optional, List

from pydantic import BaseModel, validator

from ._fields import *
from .memory import Memory


class Point(BaseModel):
    """
    Point on the map in geographic coordinates on earth.
    """

    lon: LON = Field(description="Longitude")
    lat: LAT = Field(description="Latitude")


class SiteInfo(BaseModel):
    """
    Localized information about a site.

    Description and abstract are optional and not used in all projects.
    """

    lang: LANG = LANG_FIELD
    name: NAME = Field(description="Display Name")
    abstract: Optional[TEXT] = Field(description="Short Description")
    description: Optional[LONG_TEXT] = Field(description="Long Description")

    @validator("lang")
    def validate_lang(cls, lang):
        from languager import get_language

        lang = get_language(lang).short
        if lang is None:
            raise ValueError("No ISO639-1 ID Found")
        return lang


class NewSite(BaseModel):
    """
    Describes necessary information to create a new project
    """

    id: SID = Field(description="Unique and Descriptive ID for this site")
    info: SiteInfo = Field(description="Default localization option for this project")
    location: Point = Field(description="Location of this site")
    image: Optional[IMAGE] = Field(description=IMAGE_NEW)


class Site(NewSite):
    """
    Presents a location on a map which can be augmented with memories.
    """

    image: Optional[IMAGE] = Field(description=IMAGE_TXT)
    memories_count: int = Field(ge=0, description="Total amount of published memories")
    waiting_approval: Optional[bool] = Field(
        description="If present, will tell approval status"
    )
    memories: Optional[List[Memory]] = Field(
        description="List of memories fo this site"
    )

    class Config:
        __examples__ = {
            "basic": {
                "summary": "Basic",
                "value": {

                }
            }
        }


class ModifiedSite(BaseModel):
    """
    Modifies a site
    """

    info: Optional[SiteInfo] = Field(
        description="Any modified locale data, doesn't affect default locale"
    )
    location: Optional[Point] = Field(description="If position was modified")
    image: Optional[IMAGE] = Field(description=IMAGE_NEW)

    class Config:
        __examples__ = {
            "location": {
                "summary": "Change Location",
                "value": {

                }
            },
            "image": {
                "summary": "Change Location",
                "value": {

                }
            },
            "info": {
                "summary": "Change locale",
                "value": {

                }
            },
            "delete": {
                "summary": "Delete value",
                "value": {

                }
            }
        }
