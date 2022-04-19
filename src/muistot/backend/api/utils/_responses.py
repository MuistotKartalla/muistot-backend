from textwrap import dedent

from ._doctils import d, get_samples

URL_FAILURE = d("Failed to parse the URL parameter(s)")
URL_FAILURE_CREATE_MODIFY = d(
    dedent(
        """
    Failure in parsing the request

    Response will indicate whether the URL or the entity failed to parse.
    """
    )
)
UNAUTHENTICATED = d(dedent(
    """
    The user is not authenticated or the authentication is invalid
    """
))
UNAUTHORIZED = d(
    dedent(
        """
        The user lacks privileges for this resource.
        """
    )
)
SUCCESS = d("Successful Request")
PARENTS = d("Parents were not found")
PARENTS_SELF = d("The resource or its parents were not found")


def delete():
    return {
        404: PARENTS,
        204: SUCCESS,
        422: URL_FAILURE,
        401: UNAUTHENTICATED,
        403: UNAUTHORIZED,
    }


def modify():
    return {
        404: PARENTS_SELF,
        204: SUCCESS,
        304: d("The resource was not modified"),
        422: URL_FAILURE_CREATE_MODIFY,
        401: UNAUTHENTICATED,
        403: UNAUTHORIZED,
    }


def create(conflict: bool = False):
    return {
        404: PARENTS_SELF,
        204: SUCCESS,
        304: d("The resource was not modified"),
        422: URL_FAILURE_CREATE_MODIFY,
        401: UNAUTHENTICATED,
        403: UNAUTHORIZED,
        **(
            {}
            if not conflict
            else {409: d("Resource with the same identifier already exists")}
        ),
    }


def get(model):
    return {
        404: PARENTS_SELF,
        200: {**SUCCESS, **get_samples(model)},
        422: URL_FAILURE,
        401: UNAUTHENTICATED,
        403: UNAUTHORIZED,
    }


def gets(model):
    return {
        404: d("Parents were not found"),
        200: {**SUCCESS, **get_samples(model)},
        422: URL_FAILURE,
        401: UNAUTHENTICATED,
        403: UNAUTHORIZED,
    }


__all__ = ["create", "modify", "delete", "gets", "get"]
