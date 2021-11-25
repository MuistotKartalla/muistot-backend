from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def entry():
    return {"hello": "world"}
