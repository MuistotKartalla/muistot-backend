from typing import List, Optional, Literal

from pydantic import BaseModel, Field


class Project(BaseModel):
    title: Optional[str]
    description: Optional[str]
    contentDescription: Optional[str]
    visitorPosting: bool
    image: Optional[str]

    id: int
    alkaa: Optional[str]
    loppuu: Optional[str]
    poistuu: Optional[str]

    moderators: Optional[List[int]]


class Site(BaseModel):
    id: int
    title: str
    search: str
    location: List[float] = Field(max_items=2, min_items=2)

    author: Optional[str]
    authorText: Optional[str]

    image: str = Field(default="/static/placeholder.jpg")


class Location(BaseModel):
    lat: str
    lng: str


class SiteQuery(BaseModel):
    """
    detailLevel:
        0 - coordinates, id
        1 - 0 + title, author
        2 - 1 + date, previewImage
    """
    projectId: int
    location: Location
    detailLevel: Literal[0, 1, 2]
    howMany: int
    alreadyLoadedIds: Optional[List[int]]
    onlyByUsers: Optional[List[int]]
