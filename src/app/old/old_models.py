from typing import List, Optional

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


