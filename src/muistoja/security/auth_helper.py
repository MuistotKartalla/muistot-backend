from fastapi import Request
from fastapi.security import HTTPBearer


class _BaseManager(HTTPBearer):
    def __init__(self):
        super(_BaseManager, self).__init__(
            scheme_name="Session Token Auth",
            bearerFormat="Binary Data in Base64",
            description="Contains Username and Session ID in Base64",
            auto_error=False,
        )


class _AuthManager(_BaseManager):
    def __init__(self):
        super(_AuthManager, self).__init__()

    async def __call__(self, request: Request):
        return request.user


auth_helper = _AuthManager()
"""
Manager that does nothing besides returning the user in current scope.

This is used to check if the user is authenticated.
"""

__all__ = ["auth_helper"]
