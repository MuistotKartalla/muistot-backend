from fastapi import APIRouter

router = APIRouter(tags=["Common"])


@router.get("/")
def entry():
    return {"hello": "world"}
