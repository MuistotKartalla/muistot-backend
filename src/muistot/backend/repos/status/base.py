from abc import ABC, abstractmethod
from enum import IntFlag, auto
from functools import wraps
from inspect import signature
from typing import Any, Optional, Dict, Tuple
from typing import Mapping

from starlette.exceptions import HTTPException
from starlette.status import HTTP_404_NOT_FOUND, HTTP_409_CONFLICT, HTTP_403_FORBIDDEN, HTTP_400_BAD_REQUEST

from ....database import Database
from ....logging import log
from ....security import User


class Status(IntFlag):
    NONE = auto()

    EXISTS = auto()
    DOES_NOT_EXIST = auto()

    PUBLISHED = auto()
    NOT_PUBLISHED = auto()

    OWN = auto()

    ANONYMOUS = auto()
    AUTHENTICATED = auto()

    ADMIN = auto()
    SUPERUSER = auto()

    ADMIN_POSTING = auto()
    AUTO_PUBLISH = auto()

    @staticmethod
    def construct(
            status_data: Optional[Mapping[str, Any]],
            status_mapping: Dict[str, Tuple['Status', 'Status']],
    ) -> 'Status':
        status = Status.NONE
        if status_data is not None:
            for key, (on_true, on_false) in status_mapping.items():
                if key in status_data and status_data[key]:
                    status |= on_true
                else:
                    status |= on_false
        else:
            status |= status.DOES_NOT_EXIST
        return status


class StatusProvider(ABC):
    """Checks resource existence status and any prerequisites
    """
    db: Database
    user: User
    identifiers: Dict[str, Any]

    async def provide_status(self) -> Status:
        status = Status.NONE
        if self.user.is_authenticated:
            status |= Status.AUTHENTICATED
            if self.user.is_superuser:
                status |= Status.SUPERUSER | Status.ADMIN
        else:
            status |= Status.ANONYMOUS
        return status | await self.derive_status(await self.query())

    async def query(self):
        if self.user.is_authenticated:
            return await self.db.fetch_one(
                self.query_authenticated,
                {
                    "user": self.user.identity,
                    **self.identifiers,
                }
            )
        else:
            return await self.db.fetch_one(
                self.query_anonymous,
                {
                    **self.identifiers,
                }
            )

    @property
    @abstractmethod
    def query_authenticated(self) -> str:
        """Query when the user is authenticated
        """

    @property
    @abstractmethod
    def query_anonymous(self) -> str:
        """Query when the user is not authenticated
        """

    @abstractmethod
    async def derive_status(self, m: Mapping) -> Status:
        """Checks the existence status for this instance

        This should first check that all prerequisites are filled and throw if not
        and then use the methods from Status to construct a Status.

        Mainly useful for the state decorators.

        Returns
        -------
        status
            Status-instance to check the state of this resource

        Raises
        ------
        fastapi.HTTPException
            On failure to meet prerequisites
        """


def require_status(*acceptable_statuses: Status, errors: Dict[Status, HTTPException] = None):
    errors = {} if not errors else {**errors}

    privilege_error = HTTPException(
        status_code=HTTP_403_FORBIDDEN,
        detail="Not enough privileges",
    )

    not_found_error = HTTPException(
        status_code=HTTP_404_NOT_FOUND,
        detail="Resource not found",
    )

    default_exception_mappers = {
        Status.DOES_NOT_EXIST: not_found_error,
        Status.NOT_PUBLISHED: not_found_error,
        Status.ANONYMOUS: privilege_error,
        Status.EXISTS: HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="Resource already exists",
        ),
    }

    authenticated_statuses = [Status.OWN, Status.AUTHENTICATED, Status.ADMIN, Status.SUPERUSER]
    if any(status in s for status in authenticated_statuses for s in acceptable_statuses):
        errors[Status.EXISTS | Status.PUBLISHED | Status.ANONYMOUS] = privilege_error

    if any(Status.ADMIN in s for s in acceptable_statuses):
        errors[Status.EXISTS | Status.PUBLISHED | Status.AUTHENTICATED] = privilege_error

    if any(Status.SUPERUSER in s or Status.OWN in s for s in acceptable_statuses):
        errors[Status.EXISTS | Status.PUBLISHED | Status.ANONYMOUS] = privilege_error
        errors[Status.EXISTS | Status.PUBLISHED | Status.AUTHENTICATED] = privilege_error
        errors[Status.EXISTS | Status.PUBLISHED | Status.AUTHENTICATED] = privilege_error
        errors[Status.EXISTS | Status.SUPERUSER] = privilege_error
        errors[Status.EXISTS | Status.ADMIN] = privilege_error

    def decorator(f):
        status_parameters = [name for name, param in signature(f).parameters.items() if param.annotation == Status]
        function_name = f.__name__

        @wraps(f)
        async def requirement(self: StatusProvider, *args, **kwargs):
            status = await self.provide_status()
            if any(option & status == option for option in acceptable_statuses):
                if status_parameters:
                    return await f(self, *args, **kwargs, **{name: status for name in status_parameters})
                else:
                    return await f(self, *args, **kwargs)
            else:
                log.error(
                    "Attempted to call %s() with invalid status:"
                    "\n -expected: %r"
                    "\n -presented: %r"
                    "\n -context: %r"
                    "\n -user: %r",
                    function_name,
                    acceptable_statuses,
                    status,
                    self.identifiers,
                    self.user.identity if self.user.is_authenticated else "",
                )
                for error_status, error in (
                        *errors.items(),
                        *default_exception_mappers.items(),
                ):
                    if error_status & status == error_status:
                        raise error
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail="Request failed to meet required status",
                )

        return requirement

    return decorator
