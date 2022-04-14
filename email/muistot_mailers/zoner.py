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
        f"Hei {user}! Tässä kirjautumislinkkisi muistotkartalla palveluun",
        "Kirjaudu Sisään",
        link
    )


def get_fi_template(user: str, link: str):
    return set_template_data(
        "Muistotkartalla Login",
        f"Hi {user}! Here is your muistotkartalla login link",
        "Click to Login",
        link
    )


class ZonerMailer(Mailer):
    config: MailerConfig

    def __init__(self, **kwargs):
        self.config = MailerConfig(**kwargs)

    def send_via_smtp(self, email: str, subject: str, *content: MIMEText):
        mail = MIMEMultipart("alternative")
        mail["Subject"] = subject
        mail["From"] = self.get_sender()
        mail["To"] = email
        for c in content:
            mail.attach(c)
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
            content = [
                MIMEText(get_eng_template(user, url), "html"),
                MIMEText(f"Login link: {url}", "plain")
            ]
        else:
            subject = "Muistotkartalla Kirjautuminen"
            content = [
                MIMEText(get_fi_template(user, url), "html"),
                MIMEText(f"Linkki kirjautumiseen: {url}", "plain")
            ]

        return subject, content

    def handle_verify_data(self, user: str, token: str, verified: bool, lang: str = "fi", **_):
        from urllib.parse import urlencode
        url = urlencode(dict(user=user, token=token, verified=f'{bool(verified)}'.lower()))
        url = f'{self.config.service_url}#verify-user:{url}'

        if lang == "en":
            subject = "Muistotkartalla Verification"
            content = [
                MIMEText(set_template_data(
                    "Muistotkartalla Verification",
                    f"Welcome {user}! Please take a moment to verify your account to start using muistotkartalla."
                    f"Click the button below or enter the code: {token}.",
                    "Verify Account",
                    url,
                ), "html"),
                MIMEText(f"Verify link: {url}", "plain")
            ]
        else:
            subject = "Muistotkartalla Tilin Vahvistus"
            content = [
                MIMEText(set_template_data(
                    "Muistotkartalla Tilin Vahvistus",
                    f"Tervetuloa {user}! Vahvista vielä muistotkartalla tilisi klikkaamalla alla olevaa painiketta"
                    f"tai koodilla {token}.",
                    "Vahvista Tilisi",
                    url,
                ), "html"),
                MIMEText(f"Linkki tilin vahvistamiseen: {url}", "plain")
            ]

        return subject, content

    async def send_email(self, email: str, email_type: str, **data):
        try:

            if email_type == "login":
                subject, content = self.handle_login_data(**data)
            elif email_type == "register":
                subject, content = self.handle_verify_data(**data)
            else:
                subject = "Muistotkartalla" if "subject" not in data else data["subject"]
                content = MIMEText(data.get("content", ""))

            self.send_via_smtp(email, subject, content)

            return Result(success=True)
        except BaseException as e:
            log.exception("Failed mail", exc_info=e)
            return Result(success=False)
