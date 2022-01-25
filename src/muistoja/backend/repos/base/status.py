from enum import IntEnum
from typing import Optional


class Status(IntEnum):
    DOES_NOT_EXIST = 0
    NOT_PUBLISHED = 1
    PUBLISHED = 2

    OWN = 3
    ADMIN = 4
    OWN_AND_ADMIN = OWN + ADMIN

    @staticmethod
    def resolve(value: Optional[int]) -> 'Status':
        if value is None:
            return Status.DOES_NOT_EXIST
        elif value == 1:
            return Status.PUBLISHED
        else:
            return Status.NOT_PUBLISHED
