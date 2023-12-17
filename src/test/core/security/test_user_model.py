import pytest
from muistot.security.scopes import SUPERUSER, ADMIN, MODERATOR, AUTHENTICATED
from muistot.security.user import User


def test_from_cache():
    u = User.from_cache(username="a", token="123")
    assert u.is_authenticated
    assert u.identity == u.username == u.display_name
    assert u.token == "123"
    assert not u.is_superuser


def test_non_auth_user_identity_throws():
    u = User()
    with pytest.raises(ValueError):
        print(u.identity)
    with pytest.raises(ValueError):
        print(u.display_name)


def test_superuser_is_admin():
    u = User()
    u.scopes = {SUPERUSER, AUTHENTICATED}
    u.username = "a"
    assert u.is_admin_in(None)
    assert u.is_admin_in("None")
    assert u.is_superuser
    assert u.is_authenticated


def test_superuser_admin_is_admin():
    u = User()
    assert u == User.null()
    u.scopes = {SUPERUSER, ADMIN, AUTHENTICATED}
    u.username = "a"
    u.admin_projects = ["a"]
    assert u.is_admin_in("a")


def test_null_user():
    assert User() == User.null()


def test_admin_missing_auth():
    u = User()
    u.scopes = {ADMIN}
    u.username = "a"
    u.admin_projects = ["a"]
    assert u.is_admin_in("a")
    assert not u.is_authenticated


def test_constructor():
    u = User(username="a", scopes={ADMIN, AUTHENTICATED}, admin_projects={"b"})
    assert u.is_authenticated
    assert u.is_admin_in("b")
    assert u.username == "a"

def test_moderator_is_moderator():
    u = User()
    u.scopes = {MODERATOR, AUTHENTICATED}
    u.username = "a"
    u.moderator_projects = ["a"]
    assert u.is_moderator_in("a")

def test_superuser_is_moderator():
    u = User()
    u.scopes = {SUPERUSER, AUTHENTICATED}
    u.username = "a"
    u.moderator_projects = ["a"]
    assert u.is_moderator_in("a")

def test_superuser_moderator_is_moderator():
    u = User()
    u.scopes = {SUPERUSER, MODERATOR, AUTHENTICATED}
    u.username = "a"
    u.moderator_projects = ["a"]
    assert u.is_moderator_in("a")

def test_moderator_missing_auth():
    u = User()
    u.scopes = {MODERATOR}
    u.username = "a"
    u.moderator_projects = ["a"]
    assert u.is_moderator_in("a")
    assert not u.is_authenticated