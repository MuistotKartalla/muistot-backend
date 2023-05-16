from typing import Optional, List

from pydantic import BaseModel, validator

from .datatypes import *
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
        return validate_language(lang)


class NewSite(BaseModel):
    """
    Describes necessary information to create a new project
    """

    id: SID = Field(description="Unique and Descriptive ID for this site")
    info: SiteInfo = Field(description="Default localization option for this project")
    location: Point = Field(description="Location of this site")
    image: Optional[IMAGE] = Field(description=IMAGE_NEW)

    class Config:
        __examples__ = {
            "basic": {
                "summary": "Basic",
                "value": {
                    "id": "my-awesome-site#1",
                    "info": {
                        "lang": "fin",
                        "name": "My Awesome Site!",
                        "description": "Longer info on this place"
                    },
                    "location": {
                        "lat": 60.75,
                        "lon": 24.56
                    }
                },
                "description": (
                    "__The language of the initial site info needs to match the project default.__"
                    "Even though the _info_ has a ISO639-3 language, it will be correctly converted to ISO639-1. "
                    "Many times the sites will not have images themselves, rather only the memories contain images. "
                    "This however varies per project. The capability is added here for future use. "
                    "The image needs to be a valid base64 string. "
                    "Coordinates are always in decimal degrees."
                )
            },
        }


class Site(NewSite):
    """
    Presents a location on a map which can be augmented with memories.
    """

    image: Optional[IMAGE] = Field(description=IMAGE_TXT)
    memories_count: int = Field(ge=0, description="Total amount of published memories")
    waiting_approval: Optional[bool] = Field(description="If present, will tell approval status")
    memories: Optional[List[Memory]] = Field(description="List of memories fo this site")
    own: Optional[bool] = Field(description="If this item is owned by the current user")
    creator: Optional[UID] = Field(description="The creator of this site")
    modifier: Optional[UID] = Field(description="The last modifier of this site")

    class Config:
        __examples__ = {
            "basic": {
                "summary": "Basic",
                "value": {
                    "memories_count": 10,
                    "image": "1dc15d85-8433-11ec-8f55-0242ac140005",
                    **NewSite.Config.__examples__["basic"]
                },
                "description": "Images are again strings that can be used to query the image endpoint."
            },
            "own": {
                "summary": "User's Own",
                "value": {
                    "memories_count": 10,
                    "waiting_approval": True,
                    **NewSite.Config.__examples__["basic"]
                },
                "description": "Users are able to see their own sites even if they are not published."
            }
        }


class ModifiedSite(BaseModel):
    """
    Modifies a site
    """

    location: Optional[Point] = Field(description="If position was modified")
    image: Optional[IMAGE] = Field(description=IMAGE_NEW)
    info: Optional[SiteInfo] = Field(description="Any new or modified localization")

    @validator("location")
    def validate_location(cls, value: Optional[Point]):
        assert value is not None, 'Null location is not permitted'
        return value

    class Config:
        __examples__ = {
            "location": {
                "summary": "Change Location",
                "value": {
                    "location": {
                        "lat": 70.32,
                        "lon": 34.1
                    }
                },
                "description": "The location can be present or absent, but not `null`."
            },
            "image": {
                "summary": "Delete Image",
                "value": {
                    "image": None
                },
                "description": (
                    "This explicitly deletes the image from this site."
                    " An image could also be added or changed by having the value be a valid base64 encoded image."
                )
            },
            "localize": {
                "summary": "Localize a site",
                "description": (
                    "This will change or create a new localization entry for this site."
                ),
                "value": {
                    "info": {
                        "lang": "en",
                        "name": "Awesome Site",
                        "description": "Awesome english translation"
                    }
                }
            }
        }
