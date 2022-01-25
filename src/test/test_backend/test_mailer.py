import pytest

from muistoja.backend.mailer import *


class MockMailer(Mailer):

    async def send_verify_email(self, username: str, email: str) -> bool:
        return False

    async def verify_email(self, email: str) -> bool:
        return True


def test_default_get():
    assert type(get_mailer()).__name__ == "DefaultMailer"


def test_mail_setter():
    register_mailer(MockMailer())
    assert type(get_mailer()) == MockMailer


@pytest.mark.anyio
async def test_mail_mock():
    register_mailer(MockMailer())
    assert not await get_mailer().send_verify_email("", "")
    assert await get_mailer().verify_email("")
