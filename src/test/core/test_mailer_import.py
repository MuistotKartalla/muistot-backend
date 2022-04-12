import pytest
from muistot.config import Config
from muistot.config.config import Mailer
from muistot.mailer import _derive_default


@pytest.fixture(autouse=True)
def set_default():
    old = Config.mailer
    Config.mailer = Mailer(driver=".imaginary")
    yield
    Config.mailer = old


def test_importing():
    with pytest.raises(RuntimeError) as e:
        _derive_default()
    assert e.value.args[0] == "SUCCESS"
