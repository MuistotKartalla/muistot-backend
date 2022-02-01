import abc
from dataclasses import dataclass
from threading import Lock
from typing import NoReturn, Optional

from ...core.config import Config


@dataclass
class Result:
    """
    Operation result.

    The reason is optional and meant to give a user readable message on failure.
    """
    success: bool
    reason: Optional[str] = None


class Mailer(metaclass=abc.ABCMeta):
    """
    Abstract base for a Mailer that can send mails and verify addresses
    """

    @abc.abstractmethod
    async def send_email(self, email: str, **data) -> Result:
        """
        Sends an email to a specified email
        The email should be verified first

        :param email:       Email to send to
        :return:            Result
        """
        pass

    @abc.abstractmethod
    async def verify_email(self, email: str) -> Result:
        """
        Verifies an email address

        :param email:   Address to verify
        :return:        Result
        """
        pass


instance_lock = Lock()
instance: Optional[Mailer] = None


def _derive_default() -> Mailer:
    mailer = Config.mailer
    from .default_mail import get
    return get(**mailer.dict())


def get_mailer() -> Mailer:
    """
    Gets the current mailer implementation

    :return: A Mailer instance
    """
    global instance
    with instance_lock:
        if instance is None:
            instance = _derive_default()
        return instance


def register_mailer(m: Mailer) -> NoReturn:
    """
    Registers a mailer to use for mailing

    :param m: A Mailer instance
    """
    global instance
    with instance_lock:
        instance = m


__all__ = [
    'get_mailer',
    'register_mailer',
    'Mailer',
    'Result'
]
