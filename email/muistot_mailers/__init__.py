from muistot.mailer import Mailer, Result
from .server import ServerMailer
from .zoner import ZonerMailer


class MuistotMailer(Mailer):
    DRIVERS = {
        "smtp": ZonerMailer,
        "server": ServerMailer,
        "zoner": ZonerMailer,
    }

    delegate: Mailer

    def __init__(self, driver: str = "smtp", **kwargs):
        self.delegate = MuistotMailer.DRIVERS[driver](**kwargs)

    async def send_email(self, email: str, email_type: str, **data) -> Result:
        return await self.delegate.send_email(email, email_type, **data)


__all__ = ["MuistotMailer"]
