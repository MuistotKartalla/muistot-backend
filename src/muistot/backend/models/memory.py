from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from ._fields import *


class Memory(BaseModel):
    """
    Describes a memory
    """

    id: MID = Field(description="ID of this memory")
    user: UID = Field(description="Author's ID")
    title: NAME = Field(description="Short title for this memory")
    story: Optional[TEXT] = Field(description="Longer description of this memory")
    image: Optional[IMAGE] = Field(description=IMAGE_TXT)
    modified_at: datetime = Field(description="Last modified time")
    own: Optional[bool] = Field(description="If this item is owned by the current user")

    waiting_approval: Optional[bool] = Field(
        description="Tells the approval status if present"
    )

    class Config:
        __examples__ = {
            "normal": {
                "summary": "Normal",
                "value": {

                }
            },
            "own": {
                "summary": "User's Own",
                "value": {

                }
            }
        }


class NewMemory(BaseModel):
    """
    Creates a memory
    """

    title: NAME = Field(description="Default name for this memory")
    story: Optional[TEXT] = Field(
        description="Longer description of the memory if available"
    )
    image: Optional[IMAGE] = Field(description=IMAGE_NEW)

    class Config:
        __examples__ = {
            "basic": {
                "summary": "Basic",
                "value": {

                }
            }
        }


class ModifiedMemory(BaseModel):
    """
    Model for modifying a Memory
    """

    title: Optional[NAME] = Field(description="Short memory title")
    story: Optional[TEXT] = Field(description="Longer description of this memory")
    image: Optional[IMAGE] = Field(description=IMAGE_NEW)

    class Config:
        __examples__ = {
            "basic": {
                "summary": "Basic",
                "value": {

                }
            }
        }
