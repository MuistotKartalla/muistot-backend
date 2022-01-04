import abc
from threading import Lock
from typing import NoReturn, Optional


class Mailer(metaclass=abc.ABCMeta):
    """
    Abstract base for a Mailer that can send mails and verify addresses
    """

    @abc.abstractmethod
    async def send_verify_email(self, username: str, email: str) -> bool:
        """
        Sends a verification email to a specified user
        The email should be verified first

        :param username:    Name of the user
        :param email:       Email to send to
        :return:            Success/Failure to send or queue the send operation
        """
        pass

    @abc.abstractmethod
    async def verify_email(self, email: str) -> bool:
        """
        Verifies an email address

        :param email:   Address to verify
        :return:        True only if the address is valid, False otherwise
        """
        pass


instance_lock = Lock()
instance: Optional[Mailer] = None


def get_mailer() -> Mailer:
    """
    Gets the current mailer implementation

    :return: A Mailer instance
    """
    global instance
    with instance_lock:
        if instance is None:
            from .default_mail import DefaultMailer
            instance = DefaultMailer()
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
    'Mailer'
]
