from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, validator, EmailStr

from ._fields import *
from .site import Site


class ProjectInfo(BaseModel):
    """
    Localized data for a project
    """
    lang: LANG = Field(description='Language of this info object')
    name: NAME = Field(description='Display name')
    abstract: Optional[TEXT] = Field(description='Short Description of the project')
    description: Optional[LONG_TEXT] = Field(description='Longer version of the description')

    @validator('lang')
    def validate_lang(cls, lang):
        from languager import get_language
        lang = get_language(lang).short
        if lang is None:
            raise ValueError('No ISO639-1 ID Found')
        return lang

    class Config:
        __example__ = {
            'lang': 'en',
            'name': 'My Awesome Project',
            'abstract': 'This is my super awesome project! You should totally check it out.',
            'description': '## Awesome Project\n\n- Has everything\n- Awesome'
        }


class ProjectContact(BaseModel):
    """
    Research related contacts for a project
    """
    contact_email: Optional[EmailStr] = Field(description='Contact email for the organizer')
    has_research_permit: bool = Field(description='True if this project is running with a research permit')
    can_contact: bool = Field(description="Does the project have permission to contact participants/researcher")

    class Config:
        __example__ = {
            'contact_email': 'example@exmaple.com',
            'has_research_permit': False,
            'can_contact': True
        }


class NewProject(BaseModel):
    """
    Creates a new project
    """
    id: PID = Field(default='Unique and descriptive ID for the project')
    info: ProjectInfo = Field(default='Default locale inf o for the Project')
    image: Optional[IMAGE] = Field(description=IMAGE_NEW)

    starts: Optional[datetime] = Field(description='Project Start Time')
    ends: Optional[datetime] = Field(description='Project End Time')

    admins: Optional[List[UID]] = Field(unique_items=True, description="Admins for the project")
    contact: Optional[ProjectContact] = Field(description='Project contact details if any are available')
    admin_posting: bool = Field(default=False, description="True if only admins can post")

    class Config:
        __examples__ = {
            "basic": {
                "id": "awesome-project",
                "info": ProjectInfo.Config.__example__,
                "admin_posting": False
            },
            "complex": {
                "id": "awesome-project",
                "info": ProjectInfo.Config.__example__,
                "admin_posting": False,
                "starts": "2022-01-02",
                "ends": "2022-02-03",
                "admins": [
                    "Me_MySelf_And_I"
                ],
                "contact": ProjectContact.Config.__example__,
            }
        }


class Project(NewProject):
    """
    Basic model for a Project
    """
    image: Optional[IMAGE] = Field(description=IMAGE_TXT)
    site_count: conint(ge=0) = Field(description='Number of sites this project has')
    sites: Optional[List[Site]] = Field(description='List of Sites (Optional)')

    class Config:
        __examples__ = {
            "basic": {
                "site_count": 10,
                **NewProject.Config.__examples__["basic"]
            },
            "with-image": {
                "site_count": 10,
                **NewProject.Config.__examples__["basic"],
                "image": "1dc15d85-8433-11ec-8f55-0242ac140005"
            }

        }


class ModifiedProject(BaseModel):
    """
    Used to modify project and/or its default settings.
    """
    info: Optional[ProjectInfo] = Field(description='Modifies the default locale for a project or sets a new one')
    image: Optional[IMAGE] = Field(description=IMAGE_NEW)

    starts: Optional[datetime] = Field(description='Optional start date for the project')
    ends: Optional[datetime] = Field(description='Optional end date for the project')

    admins: Optional[List[UID]] = Field(
        unique_items=True,
        description="Contains the complete Project administrator list"
    )
    contact: Optional[ProjectContact] = Field(description='Modified contact data if any')

    class Config:
        __examples__ = {
            "change-default-lang": {
                "info": ProjectInfo.Config.__example__
            },
            "replace-admins": {
                "admins": [
                    "Hello",
                    "World"
                ]
            }
        }
