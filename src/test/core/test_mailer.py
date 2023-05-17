from muistot.mailer import get_mailer
from muistot.mailer.logmailer import LogMailer


def test_defaults_to_logmailer():
    mailer = get_mailer()
    assert isinstance(mailer, LogMailer)
