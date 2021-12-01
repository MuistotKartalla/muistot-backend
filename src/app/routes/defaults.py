from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def entry(a: int):
    return {"hello": "world", "a": a}
