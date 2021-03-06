import abc
from dataclasses import dataclass
from threading import Lock
from typing import Optional

from ..config import Config


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
    Abstract base for a Mailer that can send mails
    """

    @abc.abstractmethod
    async def send_email(self, email: str, email_type: str, **data) -> Result:
        """
        Sends an email to a specified email
        The email should be verified first

        :param email:       Email to send to
        :param email_type:  Email type to send, kwargs are the arguments for this type
        :return:            Result
        """


instance_lock = Lock()
instance: Optional[Mailer] = None


def _derive_default() -> Mailer:
    import importlib
    mailer_config = Config.mailer.config
    mailer_impl = Config.mailer.driver
    return getattr(importlib.import_module(f"{mailer_impl}", __name__), "get")(**mailer_config)


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


__all__ = ["get_mailer", "Mailer", "Result"]
