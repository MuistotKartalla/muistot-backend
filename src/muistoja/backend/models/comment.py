from datetime import datetime
from textwrap import dedent
from typing import Optional

from pydantic import BaseModel

from ._fields import *


class Comment(BaseModel):
    """
    Represents a comment on an entity
    """

    id: CID = Field(description="ID of this comment")
    user: UID = Field(description="Author's ID")
    comment: SMALL_TEXT = Field(description="Content")
    modified_at: datetime = Field(description="Last modified time")
    own: Optional[bool] = Field(description="If this item is owned by the current user")
    waiting_approval: Optional[bool]

    class Config:
        __examples__ = {
            "normal": {
                "summary": "Ordinary comment",
                "value": {
                    "id": 20,
                    "user": "Master-Kenobi",
                    "comment": "Hello There",
                    "modified_at": "2005-05-19 19:30:25",
                },
            },
            "own": {
                "summary": "Authenticated user",
                "description": dedent(
                    """
                    A comments returned for **authenticated** users may contain their own comments 
                    that are not yet published.
                    """
                ),
                "value": {
                    "id": 1,
                    "user": "my username#123",
                    "comment": "Hello World",
                    "waiting_approval": True,
                    "modified_at": "2021-01-19 20:00:00",
                },
            },
        }


class ModifiedComment(BaseModel):
    """
    Represents a comment that is being modified
    """

    comment: SMALL_TEXT = Field(description="Modified content")

    class Config:
        __examples__ = {
            "basic": {
                "summary": "Basic",
                "value": {
                    "comment": "My Changed Comment"
                }
            }
        }


class NewComment(BaseModel):
    """
    Represents a new comment made by a user on another entity.

    The user identification is located automagically from the api access key.
    """

    comment: SMALL_TEXT = Field(description="Comment to make")

    class Config:
        __examples__ = {
            "basic": {
                "summary": "Basic",
                "value": {
                    "comment": "My New Comment"
                }
            }
        }
