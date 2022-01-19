from fastapi import APIRouter

router = APIRouter(tags=["Common"])


@router.get(
    "/",
    description=(
        """
        This path is for ensuring the API works.
        """
    )
)
def entry():
    return {"hello": "world"}
