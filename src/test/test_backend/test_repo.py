import pytest
from muistoja.backend.repos.base import BaseRepo


def test_inherit_bad_name():
    with pytest.raises(AssertionError):
        class TestRepoXYX(BaseRepo):
            pass


def test_mro(caplog):
    class TestRepo(BaseRepo):
        pass

    class NextRepo(TestRepo):
        pass

    assert "NextRepo not inheriting" in caplog.text


def test_no_construct(caplog):
    class TestRepo(BaseRepo):
        pass

    assert "declared in repo TestRepo" in caplog.text


def test_no_multiple_name(caplog):
    """Names can't end in s
    """
    with pytest.raises(AssertionError):
        class TestsRepo(BaseRepo):
            pass


def test_no_certain_methods():
    """No legacy methods
    """
    with pytest.raises(AssertionError):
        class TestRepo(BaseRepo):
            def _check_exists(self):
                pass
    with pytest.raises(AssertionError):
        class OtherRepo(BaseRepo):
            def _check_not_exists(self):
                pass


def test_from_other_ok():
    from muistoja.backend.repos import ProjectRepo

    class Mock:
        _user = "A"
        lang = "B"

    r = ProjectRepo(None).from_repo(Mock())
    assert r._user == "A"
    assert r.lang == "B"
