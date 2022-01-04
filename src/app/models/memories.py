from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class ProjectInfo(BaseModel):
    lang: str
    name: Optional[str]
    abstract: Optional[str]
    description: Optional[str]


class ProjectContact(BaseModel):
    contact_email: Optional[str]
    research_permit: bool


class Project(BaseModel):
    name: str
    info: ProjectInfo
    image: Optional[str]

    starts: Optional[datetime]
    ends: Optional[datetime]

    admins: Optional[List[str]]
    contact: Optional[ProjectContact]
    anonymous_posting: bool


class Comment(BaseModel):
    user: str
    comment: str


class Memory(BaseModel):
    user: str
    title: str
    story: Optional[str]
    image: Optional[str]
    comments: Optional[List[Comment]]


class Point:
    lon: float
    lat: float


class SiteInfo(BaseModel):
    lang: str
    name: Optional[str]
    abstract: Optional[str]
    description: Optional[str]


class Site(BaseModel):
    name: str
    info: SiteInfo
    location: Point
    image: Optional[str]
    memories: Optional[List[Memory]]


__all__ = [
    'Project',
    'ProjectInfo',
    'ProjectContact',

    'Comment',
    'Memory',
    'Site',
    'SiteInfo',
    'Point'
]
