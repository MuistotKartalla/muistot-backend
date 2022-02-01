import pytest

from muistoja.login.mailer import *


class MockMailer(Mailer):

    async def send_email(self, _: str, **__) -> bool:
        return False

    async def verify_email(self, _: str) -> bool:
        return True


@pytest.fixture(autouse=True, scope="function")
def _mailer():
    old = get_mailer()
    try:
        yield
    finally:
        register_mailer(old)


def test_default_get():
    assert type(get_mailer()).__name__ == "DefaultMailer"


def test_mail_setter():
    register_mailer(MockMailer())
    assert type(get_mailer()) == MockMailer


@pytest.mark.anyio
async def test_mail_mock():
    register_mailer(MockMailer())
    assert not await get_mailer().send_email("", user="")
    assert await get_mailer().verify_email("")
