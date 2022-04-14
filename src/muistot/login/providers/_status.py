from fastapi import APIRouter, Request, Response, status

router = APIRouter()


@router.get("/status", response_class=Response)
def get_status(r: Request):
    if r.user.is_authenticated:
        return Response(status_code=status.HTTP_200_OK)
    else:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
