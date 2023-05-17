import abc
from dataclasses import dataclass
from typing import Optional


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
