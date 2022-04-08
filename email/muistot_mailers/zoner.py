from muistot.mailer import Mailer
from pydantic import BaseModel


class MailerConfig(BaseModel):
    host: str
    port: int
    ssl: bool
    user: str
    password: str


class ZonerMailer(Mailer):
    config: MailerConfig

    def __init__(self, **kwargs):
        self.config = MailerConfig(**kwargs)

    async def send_mail(self, email: str, email_type: str, **data):
        pass
