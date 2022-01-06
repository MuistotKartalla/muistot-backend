from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

PID = str
SID = str
MID = int
CID = int


class ProjectInfo(BaseModel):
    lang: str
    name: str
    abstract: Optional[str]
    description: Optional[str]


class ProjectContact(BaseModel):
    contact_email: Optional[str]
    research_permit: bool


class Project(BaseModel):
    id: PID = Field(regex=r'^[a-zA-Z0-9_:-]+$')
    info: ProjectInfo
    image: Optional[str]

    starts: Optional[datetime]
    ends: Optional[datetime]

    admins: Optional[List[str]]
    contact: Optional[ProjectContact]


class Comment(BaseModel):
    id: CID
    user: str
    comment: str


class Memory(BaseModel):
    id: MID
    user: str
    title: str
    story: Optional[str]
    image: Optional[str]
    comments: Optional[List[Comment]]


class Point(BaseModel):
    lon: float
    lat: float


class SiteInfo(BaseModel):
    lang: str
    name: str
    abstract: Optional[str]
    description: Optional[str]


class Site(BaseModel):
    id: SID = Field(regex=r'^[a-zA-Z0-9_:-]+$')
    info: SiteInfo
    location: Point
    image: Optional[str]
    memories_count: int
    memories: Optional[List[Memory]]


class NewSite(BaseModel):
    id: SID = Field(regex=r'^[a-zA-Z0-9_:-]+$')
    info: SiteInfo
    location: Point
    image: Optional[str]


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

    'ModifiedMemory',
    'ModifiedSite',
    'ModifiedProject',
    'ModifiedComment',

    'PID', 'SID', 'MID', 'CID'
]
