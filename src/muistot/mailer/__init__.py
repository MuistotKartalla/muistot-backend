import abc
from dataclasses import dataclass
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


def get_mailer() -> Mailer:
    """
    Gets the current mailer implementation

    :return: A Mailer instance
    """
    import importlib
    mailer_config = Config.mailer.config
    mailer_module, _, mailer_impl = Config.mailer.driver.rpartition('.')
    return getattr(importlib.import_module(f"{mailer_module}", __name__), mailer_impl)(**mailer_config)


__all__ = ["get_mailer", "Mailer", "Result"]
