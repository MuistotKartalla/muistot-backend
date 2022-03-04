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


class LogMailer(Mailer):

    async def send_email(self, email: str, **data) -> Result:
        from ..logging import log
        import pprint
        log.info(f"Email:\n - email: {email}\n - data:\n{pprint.pprint(data, indent=2, width=200)}")
        return Result(success=True)

    async def verify_email(self, email: str) -> Result:
        import email_validator
        try:
            r = email_validator.validate_email(email, check_deliverability=False)
            return Result(success=True, reason=r.email)
        except email_validator.EmailNotValidError as e:
            return Result(success=False, reason=str(e))


instance_lock = Lock()
instance: Optional[Mailer] = None


def _derive_default() -> Mailer:
    import importlib

    if Config.mailer is None:
        return LogMailer()
    else:
        mailer_config = Config.mailer.config
        mailer_impl = Config.mailer.name
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
