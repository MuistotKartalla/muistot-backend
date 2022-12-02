import pathlib
import time
from collections import deque
from email.message import EmailMessage
from smtplib import SMTP_SSL, SMTP
from threading import Thread, Event

from muistot.logging import log
from muistot.mailer import Mailer, Result
from pydantic import BaseModel


class MailerConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str
    ssl: bool = True
    sender: str
    service_url: str
    delay: int = 10


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
    connection: SMTP

    def __init__(self, **kwargs):
        self.config = MailerConfig(**kwargs)
        self.queue = deque()
        self.flag = Event()
        self.thread = Thread(name="Zoner Mailer", target=self.send_threaded, daemon=True)
        self.thread.start()

    def __del__(self):
        self.flag.set()

    def send_threaded(self):
        while not self.flag.is_set():
            try:
                mail_order = self.queue.popleft()
                with (SMTP_SSL if self.config.ssl else SMTP)(self.config.host, port=self.config.port) as s:
                    s.login(self.config.user, self.config.password)
                    self.connection = s
                    self.handle_threaded(*mail_order)
                    while True:
                        mail_order = self.queue.popleft()
                        self.handle_threaded(*mail_order)
            except IndexError:
                time.sleep(self.config.delay)
            finally:
                if hasattr(self, "connection"):
                    del self.connection

    def send_via_smtp(self, email: str, subject: str, text: str, html: str):
        mail = EmailMessage()
        mail["Subject"] = subject
        mail["From"] = self.get_sender()
        mail["To"] = email
        mail.set_content(text)
        mail.add_alternative(html, subtype="html")
        self.connection.send_message(mail)

    def get_sender(self):
        return f"Muistotkartalla <{self.config.sender}>"

    def handle_login_data(self, user: str, token: str, verified: bool, lang: str = "fi", **_):
        from urllib.parse import urlencode
        url = urlencode(dict(user=user, token=token, verified=f'{bool(verified)}'.lower()))
        url = f'{self.config.service_url}#email-login:{url}'

        if lang == "en":
            subject = "Muistotkartalla Login"
            html = get_eng_template(user, url)
            text = f"Login link: {url}"
        else:
            subject = "Muistotkartalla Kirjautuminen"
            html = get_fi_template(user, url)
            text = f"Linkki kirjautumiseen: {url}"

        return subject, text, html

    def handle_verify_data(self, user: str, token: str, verified: bool, lang: str = "fi", **_):
        from urllib.parse import urlencode
        url = urlencode(dict(user=user, token=token, verified=f'{bool(verified)}'.lower()))
        url = f'{self.config.service_url}#verify-user:{url}'

        if lang == "en":
            subject = "Muistotkartalla Verification"
            html = set_template_data(
                "Muistotkartalla Verification",
                f"Welcome {user}! Please take a moment to verify your account to start using muistotkartalla."
                f" Click the button below or enter the code: {token}.",
                "Verify Account",
                url,
            )
            text = f"Verify link: {url}"

        else:
            subject = "Muistotkartalla Tilin Vahvistus"
            html = set_template_data(
                "Muistotkartalla Tilin Vahvistus",
                f"Tervetuloa {user}! Vahvista vielä muistotkartalla tilisi klikkaamalla alla olevaa painiketta"
                f" tai koodilla {token}.",
                "Vahvista Tilisi",
                url,
            )
            text = f"Linkki tilin vahvistamiseen: {url}"

        return subject, text, html

    def handle_threaded(self, email: str, email_type: str, data):
        try:
            if email_type == "login":
                subject, text, html = self.handle_login_data(**data)
            elif email_type == "register":
                subject, text, html = self.handle_verify_data(**data)
            else:
                subject = "Muistotkartalla" if "subject" not in data else data["subject"]
                text = data.get("content", "")
                html = None

            self.send_via_smtp(email, subject, text, html)

        except BaseException as e:
            log.exception("Failed mail", exc_info=e)

    async def send_email(self, email: str, email_type: str, **data):
        self.queue.append((email, email_type, data))
        return Result(success=True)
