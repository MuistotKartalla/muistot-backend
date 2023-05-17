from threading import Lock

from . import Result
from .abstract import Mailer


class MailCatcher(Mailer):
    LOCK = Lock()
    MAIL = {}

    async def send_email(self, email: str, email_type: str, **data) -> Result:
        with MailCatcher.LOCK:
            MailCatcher.MAIL.setdefault(email, []).append((email_type, data))
        return Result(success=True)
