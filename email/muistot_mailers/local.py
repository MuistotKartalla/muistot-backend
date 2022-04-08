"""
This is for testing
"""
import pprint
from textwrap import dedent

from muistot.mailer import Mailer, Result


class MailConfig:
    user: str = "test"
    password: str = "test"
    email: str = "no-reply@example.com"
    url: str = "maildev"
    port: int = 25
    token: str = "test"


class LocalMailer(Mailer):

    def __init__(self, *, reroute: str, **_):
        self.reroute = reroute

    async def send_email(self, email: str, email_type: str, **data) -> Result:
        try:
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from smtplib import SMTP
            cnf = MailConfig

            if email_type == "login":
                from urllib.parse import urlencode
                url = urlencode(dict(user=data["user"], token=data.pop("token"), verified=data["verified"]))
                url = f'{self.reroute}#email-login:{url}'
                user = data["user"]
                content = MIMEText(dedent(
                    f"""
                    <html>
                    <p>Hi {user}!<p>
                    <p><a href="{url}">Login to Muistotkartalla</a></p>
                    </html>
                    """
                ), "html")
            else:
                content = MIMEText(pprint.pformat(data, indent=2, width=200))

            sender = f"Muistotkartalla <{cnf.user if cnf.email is None else cnf.email}>"
            mail = MIMEMultipart("alternative")
            mail["Subject"] = "Muistotkartalla" if "subject" not in data else data["subject"]
            mail["From"] = sender
            mail["To"] = email
            mail.attach(content)

            with SMTP(cnf.url, port=cnf.port) as s:
                s.login(cnf.user, cnf.password)
                s.send_message(mail)

            return Result(success=True)
        except BaseException as e:
            return Result(success=False, reason=str(e))
