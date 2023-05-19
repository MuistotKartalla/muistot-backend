import time
from collections import deque
from email.message import EmailMessage
from smtplib import SMTP_SSL, SMTP
from threading import Thread, Event
from urllib.parse import urlencode

from pydantic import BaseModel

from .abstract import Mailer, Result
from .templates import get_login_template
from ..logging import log


class MailerConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str
    ssl: bool = True
    sender: str
    service_url: str
    delay: int = 5


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

    def handle_login_data(
            self,
            user: str,
            token: str,
            verified: bool,
            lang: str = "en",
            **_,
    ):
        url = urlencode(dict(user=user, token=token, verified=f"{bool(verified)}".lower()))
        url = f"{self.config.service_url}#email-login:{url}"
        html = get_login_template(lang, user, url)
        if lang == "fi":
            subject = "Muistotkartalla Kirjautuminen"
            text = f"Linkki kirjautumiseen: {url}"
        else:
            subject = "Muistotkartalla Login"
            text = f"Login link: {url}"
        return subject, text, html

    def handle_threaded(self, email: str, email_type: str, data):
        try:
            if email_type == "login":
                subject, text, html = self.handle_login_data(**data)
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
