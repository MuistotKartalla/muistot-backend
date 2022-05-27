import datetime

import pytest
from muistot.backend.api.publish import PUPOrder, BAD_TYPE, BAD_PARENTS_CNT, BAD_PARENTS
from muistot.backend.models import SiteInfo, ProjectInfo, NewProject
from muistot.backend.models.user import _UserBase
from muistot.security import User
from pydantic import ValidationError


def test_invalid_iso_lang():
    for m in (SiteInfo, ProjectInfo):
        with pytest.raises(ValidationError) as e:
            m(name="a", lang="ggg")
        assert "ISO" in e.value.errors()[0]["msg"]


def test_ok_iso_lang():
    for m in (SiteInfo, ProjectInfo):
        m(name="a", lang="fi")
        m(name="a", lang="fin")


def test_user():
    u = User.from_cache(username="abcd", token="abcd")
    assert u.username == u.identity == u.display_name
    u = User.null()
    assert u.username is None
    with pytest.raises(ValueError):
        print(u.identity)
    with pytest.raises(ValueError):
        print(u.display_name)


@pytest.mark.parametrize("item_type,item_id,parent_tests", [
    ("site", "aaaa", [
        None,
        dict(memory=1),
        dict(site="aaaa"),
    ]),
    ("memory", 1, [
        None,
        dict(project="aaaa", memory=1),
        dict(site="aaaa", memory=1),
    ]),
    ("comment", 1, [
        None,
    ]),
])
def test_pup_parents_wrong(item_type, item_id, parent_tests):
    for parents in parent_tests:
        with pytest.raises(ValidationError) as e:
            PUPOrder(type=item_type, parents=parents, identifier=item_id)
        assert BAD_PARENTS in str(e.value)


@pytest.mark.parametrize("item_type,item_id,parent_tests", [
    ("site", "aaaa", [
        {},
        dict(project="aaaa", site="aaaa", memory=1),
        dict(project="aaaa", site="aaaa"),
    ]),
    ("memory", 1, [
        dict(project="aaaa", site="aaaa", memory=1),
        dict(site="aaaa"),
    ]),
    ("comment", 1, [
        dict(project="aaaa"),
        dict(site="aaaa", project="aaaa"),
    ]),
    ("project", "aaaa", [
        dict(project="aaaa")
    ])
])
def test_pup_parents_wrong_cnt(item_type, item_id, parent_tests):
    for parents in parent_tests:
        with pytest.raises(ValidationError) as e:
            PUPOrder(type=item_type, parents=parents, identifier=item_id)
        assert BAD_PARENTS_CNT in str(e.value)


@pytest.mark.parametrize("item_type,item_id,parent_tests", [
    ("site", "aaaa", [
        dict(project=1),
    ]),
    ("memory", 1, [
        dict(project="aaaa", site=1),
        dict(project=1, site="aaaa"),
        dict(project=1, site=1),
    ]),
    ("comment", 1, [
        dict(project=1, site="aaaa", memory=1),  # bad project id type
        dict(project="aaaa", site=1, memory=1),  # bad site id type
        dict(project="aaaa", site="aaaa", memory="aaaa"),  # bad memory id type

        dict(project=1, site=1, memory=1),  # Bad project and site
        dict(project=1, site="aaaa", memory="aaaa"),  # Bad project and memory
        dict(project="aaaa", site=1, memory="aaaa"),  # Bad site and memory

        dict(project=1, site=1, memory="aaaa"),  # Bad all
    ]),
    ("project", 1, [  # Bad project id type
        None
    ]),
    ("memory", "aaaa", [  # Bad memory id type
        dict(project="aaaa", site="aaaa")
    ]),
    ("site", 1, [  # Bad site id type
        dict(project="aaaa")
    ]),
    ("comment", "aaaa", [  # Bad comment id type
        dict(project="aaaa", site="aaaa", memory=1)
    ]),
])
def test_pup_parent_types(item_type, item_id, parent_tests):
    for parents in parent_tests:
        with pytest.raises(ValidationError) as e:
            PUPOrder(type=item_type, parents=parents, identifier=item_id)
        assert BAD_TYPE in str(e.value)


def test_good_pup():
    PUPOrder(type="comment", parents={"memory": 1, "site": "aaaa", "project": "aaaa"}, identifier=1)
    PUPOrder(type="project", parents={}, identifier="aaaa")
    PUPOrder(type="project", parents=None, identifier="aaaa")


def test_project_dates():
    with pytest.raises(ValidationError) as e:
        NewProject(
            id="aaaaaa",
            info=ProjectInfo(name="aaaa", lang="fi"),
            starts=datetime.datetime.fromisoformat("2022-01-01"),
            ends=datetime.datetime.fromisoformat("2021-01-01")
        )
    assert "end before start" in str(e.value)


def test_project_none_admins_raises():
    with pytest.raises(ValidationError) as e:
        NewProject(
            id="aaaaaa",
            info=ProjectInfo(name="aaaa", lang="fi"),
            admins=None
        )
    assert "not iterable" in str(e.value)


def test_user_country_validator_invalid_none():
    with pytest.raises(ValidationError):
        _UserBase(country="xx")


def test_user_country_validator_alpha3_none():
    with pytest.raises(ValidationError):
        _UserBase(country="EAZ")


def test_user_country_validator_alpha3():
    b = _UserBase(country="FIN")
    assert b.country == "FIN"


def test_user_country_validator_alpha2():
    b = _UserBase(country="FI")
    assert b.country == "FIN"


def test_user_country_subdiv_raise():
    with pytest.raises(ValidationError):
        _UserBase(country="Gb-bKm")
