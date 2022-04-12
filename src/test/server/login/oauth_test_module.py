from fastapi import APIRouter

router = APIRouter()


@router.get("/test")
def route_test():
    return dict()


def initialize(raise_on_init=False, **_):
    print('Init')
    if raise_on_init:
        raise RuntimeError("Raised")
    else:
        return router
