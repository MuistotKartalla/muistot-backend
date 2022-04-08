import pathlib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP_SSL

from muistot.logging import log
from muistot.mailer import Mailer, Result
from pydantic import BaseModel


class MailerConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str

    sender: str
    service_url: str


with open(pathlib.Path(__file__).parent / "zoner_template.html", "r") as f:
    TEMPLATE = f.read()


def set_template_data(subject: str, title: str, button: str, link: str):
    return TEMPLATE.replace(
        "${{SUBJECT}}", subject
    ).replace(
        "${{TITLE}}", title
    ).replace(
        "${{BUTTON}}", button
    ).replace(
        "${{LINK}}", link
    )


def get_eng_template(user: str, link: str):
    return set_template_data(
        "Muistotkartalla Kirjautuminen",
        f"Hei {user}! Tässä kirjautumislinkkisi muistotkartalla.fi palveluun.",
        "Kirjaudu Sisään",
        link
    )


def get_fi_template(user: str, link: str):
    return set_template_data(
        "Muistotkartalla Login",
        f"Hi {user}! Here is your muistotkartalla.fi login link.",
        "Click to Login",
        link
    )


class ZonerMailer(Mailer):
    config: MailerConfig

    def __init__(self, **kwargs):
        self.config = MailerConfig(**kwargs)

    def send_via_smtp(self, email: str, subject: str, content: MIMEText):
        mail = MIMEMultipart("alternative")
        mail["Subject"] = subject
        mail["From"] = self.get_sender()
        mail["To"] = email
        mail.attach(content)
        with SMTP_SSL(self.config.host, port=self.config.port) as s:
            s.login(self.config.user, self.config.password)
            s.send_message(mail)

    def get_sender(self):
        return f"Muistotkartalla <{self.config.sender}>"

    def handle_login_data(self, user: str, token: str, verified: bool, lang: str = "fi", **_):
        from urllib.parse import urlencode
        url = urlencode(dict(user=user, token=token, verified=f'{bool(verified)}'.lower()))
        url = f'{self.config.service_url}#email-login:{url}'

        if lang == "en":
            subject = "Muistotkartalla Login"
            content = MIMEText(get_eng_template(user, url), "html")
        else:
            subject = "Muistotkartalla Kirjautuminen"
            content = MIMEText(get_fi_template(user, url), "html")

        return subject, content

    async def send_email(self, email: str, email_type: str, **data):
        try:

            if email_type == "login":
                subject, content = self.handle_login_data(**data)
            else:
                subject = "Muistotkartalla" if "subject" not in data else data["subject"]
                content = MIMEText(data.get("content", ""))

            self.send_via_smtp(email, subject, content)

            return Result(success=True)
        except BaseException as e:
            log.exception("Failed mail", exc_info=e)
            return Result(success=False)
