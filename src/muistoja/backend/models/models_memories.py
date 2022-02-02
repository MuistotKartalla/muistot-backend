from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, constr, conint, confloat

_IMAGE_TXT = 'Image file name to be fetched from the image endpoint'
_IMAGE_NEW = 'Image data in base64'
IMAGE = constr(strict=True, strip_whitespace=True, min_length=1)

__ID_REGEX = r'^[a-zA-Z0-9-_]+$'
__ID_TYPE_STR = constr(
    strip_whitespace=True,
    min_length=4,
    max_length=250,
    regex=__ID_REGEX
)
__ID_TYPE_INT = conint(gt=0)

UID = constr(
    strip_whitespace=True,
    min_length=4,
    max_length=64,
    regex=r'^[a-zA-Z0-9-_@.: ]+$'
)

PID = __ID_TYPE_STR
SID = __ID_TYPE_STR
MID = __ID_TYPE_INT
CID = __ID_TYPE_INT

LAT = confloat(ge=-90, le=90)
LON = confloat(ge=-180, le=180)

COMMENT = constr(strip_whitespace=True, min_length=1, max_length=2500)
LANG = constr(strip_whitespace=True, min_length=2, max_length=5)
NAME = constr(strip_whitespace=True, min_length=4, max_length=200)
LONG_TEXT = constr(strip_whitespace=True, max_length=10_000)


class Comment(BaseModel):
    """
    Represents a comment on an entity
    """
    id: CID = Field(description="ID of this comment")
    user: UID = Field(description="Author's ID")
    comment: COMMENT = Field(description='Content')
    modified_at: datetime = Field(description="Last modified time")

    waiting_approval: Optional[bool]


class UserComment(Comment):
    """
    Comment model for user specific listings
    """
    project: PID = Field(description='Project the comment connects to')
    site: SID = Field(description='Site the comment connects to')
    memory: MID = Field(description='Memory the comment connects to')


class Memory(BaseModel):
    """
    Describes a memory
    """
    id: MID = Field(description="ID of this memory")
    user: UID = Field(description="Author's ID")
    title: NAME = Field(description='Short title for this memory')
    story: Optional[COMMENT] = Field(description='Longer description of this memory')
    image: Optional[IMAGE] = Field(description=_IMAGE_TXT)
    comments_count: int = Field(ge=0, description="Amount of comments on this memory")
    modified_at: datetime = Field(description='LAst modified time')

    waiting_approval: Optional[bool] = Field(description='Tells the approval status if present')

    comments: Optional[List[Comment]] = Field(description='Optional list of comments for this memory')


class UserMemory(Memory):
    """
    Memory model for user specific listings
    """
    project: PID = Field(description='Project this memory connects to')
    site: SID = Field(description='Site this memory connects to')


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
    lang: LANG = Field(description='Language of this info object')
    name: NAME = Field(description="Display Name")
    abstract: Optional[COMMENT] = Field(description="Short Description")
    description: Optional[LONG_TEXT] = Field(description="Long Description")


class NewSite(BaseModel):
    """
    Describes necessary information to create a new project
    """
    id: SID = Field(description="Unique and Descriptive ID for this site")
    info: SiteInfo = Field(description="Default localization option for this project")
    location: Point = Field(description='Location of this site')
    image: Optional[IMAGE] = Field(description=_IMAGE_NEW)


class Site(NewSite):
    """
    Presents a location on a map which can be augmented with memories.
    """
    image: Optional[IMAGE] = Field(description=_IMAGE_TXT)
    memories_count: int = Field(ge=0, description="Total amount of published memories")
    waiting_approval: Optional[bool] = Field(description="If present, will tell approval status")
    memories: Optional[List[Memory]] = Field(description="List of memories fo this site")


class ProjectInfo(BaseModel):
    """
    Localized data for a project
    """
    lang: LANG = Field(description='Language of this info object')
    name: NAME = Field(description='Display name')
    abstract: Optional[COMMENT] = Field(description='Short Description of the project')
    description: Optional[LONG_TEXT] = Field(description='Longer version of the description')


class ProjectContact(BaseModel):
    """
    Research related contacts for a project
    """
    contact_email: Optional[str] = Field(description='Contact email for the organizer')
    has_research_permit: bool = Field(description='True if this project is running with a research permit')
    can_contact: bool = Field(description="Does the project have permission to contact participants/researcher")


class NewProject(BaseModel):
    """
    Creates a new project
    """
    id: PID = Field(default='Unique and descriptive ID for the project')
    info: ProjectInfo = Field(default='Default locale inf o for the Project')
    image: Optional[IMAGE] = Field(description=_IMAGE_NEW)

    starts: Optional[datetime] = Field(description='Project Start Time')
    ends: Optional[datetime] = Field(description='Project End Time')

    admins: Optional[List[UID]] = Field(unique_items=True, description="Admins for the project")
    contact: Optional[ProjectContact] = Field(description='Project contact details if any are available')
    admin_posting: bool = Field(default=False, description="Whether the project allows users to post")


class Project(NewProject):
    """
    Basic model for a Project
    """
    image: Optional[IMAGE] = Field(description=_IMAGE_TXT)
    site_count: conint(ge=0) = Field(description='Number of sites this project has')
    sites: Optional[List[Site]] = Field(description='List of Sites (Optional)')


class NewMemory(BaseModel):
    """
    Creates a memory
    """
    title: NAME = Field(description='Default name for this memory')
    story: Optional[LONG_TEXT] = Field(description='Longer description of the memory if available')
    image: Optional[IMAGE] = Field(description=_IMAGE_NEW)


class ModifiedSite(BaseModel):
    """
    Modifies a memory
    """
    info: Optional[SiteInfo] = Field(description="Any modified locale data, doesn't affect default locale")
    location: Optional[Point] = Field(description='If position was modified')
    image: Optional[IMAGE] = Field(description=_IMAGE_NEW)


class ModifiedMemory(BaseModel):
    """
    Model for modifying a Memory
    """
    title: Optional[NAME] = Field(description='Short memory title')
    story: Optional[LONG_TEXT] = Field(description='Longer description of this memory')
    image: Optional[IMAGE] = Field(description=_IMAGE_NEW)


class ModifiedProject(BaseModel):
    """
    Used to modify project and/or its default settings.
    """
    info: Optional[ProjectInfo] = Field(description='Modifies the default locale for a project or sets a new one')
    image: Optional[IMAGE] = Field(description=_IMAGE_NEW)

    starts: Optional[datetime] = Field(description='Optional start date for the project')
    ends: Optional[datetime] = Field(description='Optional end date for the project')

    admins: Optional[List[UID]] = Field(
        unique_items=True,
        description="Contains the complete Project administrator list"
    )
    contact: Optional[ProjectContact] = Field(description='Modified contact data if any')


class ModifiedComment(BaseModel):
    """
    Represents a comment that is being modified
    """
    comment: COMMENT = Field(description="Modified content")


class NewComment(BaseModel):
    """
    Represents a new comment made by a user on another entity.

    The user identification is located automagically from the api access key.
    """
    comment: COMMENT = Field(description="Comment to make")


class Sites(BaseModel):
    """
    Sites Collection
    """
    items: List[Site] = Field(min_items=0, description="List of Sites in the current collection")


class Projects(BaseModel):
    """
    Projects Collection
    """
    items: List[Project] = Field(min_items=0, description="List of Projects in the current collection")


class Memories(BaseModel):
    """
    Memories Collection
    """
    items: List[Memory] = Field(min_items=0, description="List of Memories in the current collection")


class Comments(BaseModel):
    """
    Comments Collection
    """
    items: List[Comment] = Field(min_items=0, description="List of Comments in the current collection")


__all__ = [
    'Project',
    'ProjectInfo',
    'ProjectContact',

    'Comment',
    'Memory',
    'Site',
    'SiteInfo',
    'Point',

    'NewSite',
    'NewMemory',
    'NewComment',
    'NewProject',

    'ModifiedMemory',
    'ModifiedSite',
    'ModifiedProject',
    'ModifiedComment',

    'PID', 'SID', 'MID', 'CID',

    'Sites',
    'Projects',
    'Memories',
    'Comments',

    'UserComment',
    'UserMemory'
]
