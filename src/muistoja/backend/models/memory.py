from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel

from ._fields import *
from .comment import Comment


class Memory(BaseModel):
    """
    Describes a memory
    """
    id: MID = Field(description="ID of this memory")
    user: UID = Field(description="Author's ID")
    title: NAME = Field(description='Short title for this memory')
    story: Optional[TEXT] = Field(description='Longer description of this memory')
    image: Optional[IMAGE] = Field(description=IMAGE_TXT)
    comments_count: int = Field(ge=0, description="Amount of comments on this memory")
    modified_at: datetime = Field(description='LAst modified time')

    waiting_approval: Optional[bool] = Field(description='Tells the approval status if present')

    comments: Optional[List[Comment]] = Field(description='Optional list of comments for this memory')

    class Config:
        __examples__ = {
            "normal": {

            },
            "own": {

            }
        }


class NewMemory(BaseModel):
    """
    Creates a memory
    """
    title: NAME = Field(description='Default name for this memory')
    story: Optional[TEXT] = Field(description='Longer description of the memory if available')
    image: Optional[IMAGE] = Field(description=IMAGE_NEW)

    class Config:
        __examples__ = {
            "basic": {

            }
        }


class ModifiedMemory(BaseModel):
    """
    Model for modifying a Memory
    """
    title: Optional[NAME] = Field(description='Short memory title')
    story: Optional[TEXT] = Field(description='Longer description of this memory')
    image: Optional[IMAGE] = Field(description=IMAGE_NEW)

    class Config:
        __examples__ = {
            "basic": {

            }
        }
