from typing import Callable

from fastapi import Response, status, APIRouter
from headers import LOCATION


def created(url: str) -> Response:
    return Response(status_code=status.HTTP_201_CREATED, headers={LOCATION: url})


def modified(url: Callable[[], str], was_modified: bool) -> Response:
    if was_modified:
        return Response(
            status_code=status.HTTP_204_NO_CONTENT, headers={LOCATION: url()}
        )
    else:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)


def deleted(url: str) -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers={LOCATION: url})


def make_router(**kwargs) -> APIRouter:
    from functools import partial

    router = APIRouter(**kwargs)

    error_404 = {"description": "Requested resource was not found"}

    error_406 = {
        "description": "Failure in localization. Either language not supported or missing locale for object."
    }

    error_409 = {"description": "Conflicting identities."}

    not_found = {
        404: error_404,
    }
    conflict = {404: error_404, 409: error_409, 406: error_406}

    router.get = partial(
        router.get,
        response_model_exclude_none=True,
        responses={404: error_404, 406: error_406},
    )
    router.post = partial(
        router.post, response_model_exclude_none=True, responses=conflict
    )
    router.put = partial(
        router.put, response_model_exclude_none=True, responses=not_found
    )
    router.patch = partial(
        router.patch, response_model_exclude_none=True, responses=conflict
    )
    router.delete = partial(
        router.delete, response_model_exclude_none=True, responses=not_found
    )

    return router
