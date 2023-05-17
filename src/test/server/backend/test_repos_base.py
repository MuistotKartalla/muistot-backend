import pytest

from muistot.backend.repos.base import BaseRepo
from muistot.backend.repos.exists.base import Exists, Status


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
    from muistot.backend.repos import ProjectRepo

    class Mock:
        user = "A"
        lang = "B"

    r = ProjectRepo(None).from_repo(Mock())
    assert r.user == "A"
    assert r.lang == "B"


def test_indirect_inherit_warns(caplog):
    class A:
        pass

    class BaExists(A, Exists):
        pass

    assert BaExists.__name__ in caplog.text

    caplog.clear()

    class CaExists(Exists):
        pass

    class DaExists(CaExists):
        pass

    assert DaExists.__name__ in caplog.text


def test_bad_name_raises(caplog):
    with pytest.raises(AssertionError):
        class A(Exists):
            pass


def test_status_maintains_state():
    s = Status.OWN
    assert s.own and not s.published
    s |= Status.PUBLISHED
    assert s.own and s.published


def test_status_super_is_admin():
    s = Status.SUPER
    assert s.admin
