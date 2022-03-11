import pytest
from muistoja.backend.models import SiteInfo, ProjectInfo
from muistoja.security import User
from pydantic import ValidationError


def test_invalid_iso_lang():
    for m in (SiteInfo, ProjectInfo):
        with pytest.raises(ValidationError) as e:
            m(name="a", lang="ggg")
        assert "ISO" in e.value.errors()[0]["msg"]


def test_user():
    u = User.from_cache(username="abcd", token="abcd")
    assert u.username == u.identity == u.display_name
    u = User.null()
    assert u.username is None
    with pytest.raises(ValueError):
        print(u.identity)
    with pytest.raises(ValueError):
        print(u.display_name)
