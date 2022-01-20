# noinspection PyUnresolvedReferences
from typing import List, Dict, Literal, Any, Optional, Union, Callable

# noinspection PyUnresolvedReferences
from fastapi import APIRouter, status, Request, HTTPException
# noinspection PyUnresolvedReferences
from fastapi.responses import JSONResponse

# noinspection PyUnresolvedReferences
from ..database import *
# noinspection PyUnresolvedReferences
from ..headers import LOCATION
# noinspection PyUnresolvedReferences
from ..models import *
# noinspection PyUnresolvedReferences
from ..repos import *
# noinspection PyUnresolvedReferences
from ..security import require_auth, scopes


def created(url: str) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        headers={LOCATION: url}
    )


def modified(url: Callable[[], str], was_modified: bool) -> JSONResponse:
    if was_modified:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            headers={LOCATION: url()}
        )
    else:
        return JSONResponse(status_code=status.HTTP_304_NOT_MODIFIED)


def deleted(url: str) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={LOCATION: url}
    )


def make_router(**kwargs) -> APIRouter:
    from functools import partial

    router = APIRouter(**kwargs)

    not_found = {
        '404': {},
    }
    conflict = {
        '404': {},
        '409': {},
        '406': {}
    }

    router.get = partial(router.get, response_model_exclude_none=True, responses={
        '404': {},
        '406': {}
    })
    router.post = partial(router.post, response_model_exclude_none=True, responses=conflict)
    router.put = partial(router.put, response_model_exclude_none=True, responses=not_found)
    router.patch = partial(router.patch, response_model_exclude_none=True, responses=conflict)
    router.delete = partial(router.delete, response_model_exclude_none=True, responses=not_found)

    return router
