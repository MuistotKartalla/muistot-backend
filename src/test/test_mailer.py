from app.mailer import *


class MockMailer(Mailer):

    def send_verify_email(self, username: str, email: str) -> bool:
        pass

    def verify_email(self, email: str) -> bool:
        pass


def test_default_get():
    assert type(get_mailer()).__name__ == "DefaultMailer"


def test_mail_setter():
    register_mailer(MockMailer())
    assert type(get_mailer()) == MockMailer
