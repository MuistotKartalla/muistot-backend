from muistot.mailer.templates import get_login_template


def test_template_loading_is_ok():
    template = get_login_template("fi", "username", "https://localhost")
    assert template is not None
