from typing import List, Optional

from pydantic import BaseModel, Field


class Project(BaseModel):
    pass


class Site(BaseModel):
    id: int
    title: str
    search: str
    location: List[float] = Field(max_items=2, min_items=2)

    author: Optional[str]
    authorText: Optional[str]

    image: str = Field(default="/static/placeholder.jpg")


