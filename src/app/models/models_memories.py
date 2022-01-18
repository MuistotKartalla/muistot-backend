from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

PID = str
SID = str
MID = int
CID = int


class Comment(BaseModel):
    id: CID
    user: str
    comment: str
    modified_at: datetime

    waiting_approval: Optional[bool]


class UserComment(Comment):
    project: PID
    site: SID
    memory: MID


class Memory(BaseModel):
    id: MID
    user: str
    title: str
    story: Optional[str]
    image: Optional[str]
    comments_count: int
    modified_at: datetime

    waiting_approval: Optional[bool]

    comments: Optional[List[Comment]]


class UserMemory(Memory):
    project: PID
    site: SID


class Point(BaseModel):
    lon: float
    lat: float


class SiteInfo(BaseModel):
    lang: str
    name: str
    abstract: Optional[str]
    description: Optional[str]


class NewSite(BaseModel):
    id: SID = Field(regex=r'^[a-zA-Z0-9_:-]+$')
    info: SiteInfo
    location: Point
    image: Optional[str]


class Site(NewSite):
    memories_count: int

    waiting_approval: Optional[bool]

    memories: Optional[List[Memory]]


class ProjectInfo(BaseModel):
    lang: str
    name: str
    abstract: Optional[str]
    description: Optional[str]


class ProjectContact(BaseModel):
    contact_email: Optional[str]
    has_research_permit: bool
    can_contact: bool


class NewProject(BaseModel):
    id: PID = Field(regex=r'^[a-zA-Z0-9_:-]+$')
    info: ProjectInfo
    image: Optional[str]

    starts: Optional[datetime]
    ends: Optional[datetime]

    admins: Optional[List[str]]
    contact: Optional[ProjectContact]
    anonymous_posting: bool = False


class Project(NewProject):
    site_count: int
    sites: Optional[List[Site]]


class NewMemory(BaseModel):
    title: str
    story: Optional[str]
    image: Optional[str]


class ModifiedSite(BaseModel):
    info: Optional[SiteInfo]
    location: Optional[Point]
    image: Optional[str]


class ModifiedMemory(BaseModel):
    title: Optional[str]
    story: Optional[str]
    image: Optional[str]


class ModifiedProject(BaseModel):
    info: Optional[ProjectInfo]
    image: Optional[str]

    starts: Optional[datetime]
    ends: Optional[datetime]

    admins: Optional[List[str]]
    contact: Optional[ProjectContact]


class ModifiedComment(BaseModel):
    comment: str


class NewComment(BaseModel):
    comment: str


class Sites(BaseModel):
    items: List[Site]


class Projects(BaseModel):
    items: List[Project]


class Memories(BaseModel):
    items: List[Memory]


class Comments(BaseModel):
    items: List[Comment]


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
