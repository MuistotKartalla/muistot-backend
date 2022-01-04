from typing import Optional

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def entry(a: Optional[int] = 0):
    return {"hello": "world", "a": a}
