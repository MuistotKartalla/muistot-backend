from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, validator, EmailStr

from ._fields import *
from .site import Site


class ProjectInfo(BaseModel):
    """
    Localized data for a project
    """

    lang: LANG = Field(description="Language of this info object")
    name: NAME = Field(description="Display name")
    abstract: Optional[TEXT] = Field(description="Short Description of the project")
    description: Optional[LONG_TEXT] = Field(description="Longer version of the description")

    @validator("lang")
    def validate_lang(cls, lang):
        from languager import get_language

        lang = get_language(lang).short
        if lang is None:
            raise ValueError("No ISO639-1 ID Found")
        return lang

    class Config:
        __examples__ = {
            "basic": {
                "summary": "ISO639-1",
                "value": {
                    "lang": "en",
                    "name": "Hello World"
                }
            },
            "alternative": {
                "summary": "ISO639-3",
                "value": {
                    "lang": "eng",
                    "name": "Hello World"
                },
                "description": "ISO639-3 values get converted to ISO639-1 or rejected if one is "
                               "not found or not supported."
            }
        }


class ProjectContact(BaseModel):
    """
    Research related contacts for a project
    """

    contact_email: Optional[EmailStr] = Field(description="Contact email for the organizer")
    has_research_permit: bool = Field(description="True if this project is running with a research permit")
    can_contact: bool = Field(description="Does the project have permission to contact participants/researcher")

    class Config:
        __example__ = {
            "contact_email": "example@exmaple.com",
        }


class NewProject(BaseModel):
    """
    Creates a new project.
    """

    id: PID = Field(default="Unique and descriptive ID for the project")
    info: ProjectInfo = Field(default="Default locale info for the Project")
    image: Optional[IMAGE] = Field(description=IMAGE_NEW)

    starts: Optional[datetime] = Field(description="Project Start Time.")
    ends: Optional[datetime] = Field(description="Project End Time.")

    admins: Optional[List[UID]] = Field(default_factory=list, unique_items=True, description="Admins for the project.")
    contact: Optional[ProjectContact] = Field(description="Project contact details if any are available.")
    admin_posting: bool = Field(default=False, description="True if only admins can post")

    class Config:
        __examples__ = {
            "basic": {
                "summary": "Basic",
                "value": {
                    "id": "awesome-project",
                    "info": {
                        "lang": "en",
                        "name": "My Awesome Project"
                    },
                    "admin_posting": False,
                },
            },
            "complex": {
                "summary": "Complex",
                "value": {
                    "id": "awesome-project",
                    "info": {
                        "lang": "en",
                        "name": "My Awesome Project"
                    },
                    "admin_posting": False,
                    "starts": "2022-01-02",
                    "ends": "2022-02-03",
                    "admins": ["Me_MySelf_And_I"],
                    "contact": ProjectContact.Config.__example__,
                },
            },
        }


class Project(NewProject):
    """
    Basic model for a Project
    """

    image: Optional[IMAGE] = Field(description=IMAGE_TXT)
    sites_count: conint(ge=0) = Field(description="Number of sites this project has")
    sites: Optional[List[Site]] = Field(description="List of Sites (Optional)")

    class Config:
        __examples__ = {
            "basic": {
                "summary": "Basic",
                "value": {
                    "site_count": 10,
                    **NewProject.Config.__examples__["basic"]["value"],
                },
            },
            "image": {
                "summary": "With Image",
                "value": {
                    "site_count": 10,
                    **NewProject.Config.__examples__["basic"]["value"],
                    "image": "1dc15d85-8433-11ec-8f55-0242ac140005",
                },
                "description": "The image needs to be fetched from the _images_ endpoint.",
            },
        }


class ModifiedProject(BaseModel):
    """
    Used to modify project and/or its default settings.
    """

    image: Optional[IMAGE] = Field(description=IMAGE_NEW)
    starts: Optional[datetime] = Field(description="Optional start date for the project")
    ends: Optional[datetime] = Field(description="Optional end date for the project")
    contact: Optional[ProjectContact] = Field(description="Modified contact data if any")
    info: Optional[ProjectInfo] = Field(description="Modified or created info")

    class Config:
        __examples__ = {
            "change": {
                "summary": "Change Language",
                "value": {
                    "starts": "2022-01-01",
                    "ends": "2022-02-01",
                    "contact": {
                        "contact_email": "example@example.com"
                    },
                    "info": {
                        "lang": "eng",
                        "name": "This Will Replace",
                        "description": "OR Create a new Entry",
                    }
                },
                "description": "Changes values that are present",
            },
            "delete": {
                "summary": "Delete a value",
                "value": {
                    "starts": None
                },
                "description": "Explicit null deletes a value."
            }
        }
