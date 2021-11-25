from . import Mailer


class DefaultMailer(Mailer):

    def send_verify_email(self, username: str, email: str) -> bool:
        pass

    def verify_email(self, email: str) -> bool:
        pass
