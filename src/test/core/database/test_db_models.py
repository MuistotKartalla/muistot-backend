from muistoja.database.models import ResultSet, ResultSetCursor


def test_list_spread():
    expected = dict(a=1, b='b', c=False, d=None)
    data = ResultSet(expected.items())
    assert list(expected.values()) == list(data)


def test_dict_spread():
    expected = dict(a=1, b='b', c=False, d=None)
    data = ResultSet(expected.items())
    assert expected == {**data}


def test_variable_spread():
    expected = dict(a=1, b='b', c=False, d=None)
    data = ResultSet(expected.items())
    a, b, c, d = data
    assert a == expected['a']
    assert b == expected['b']
    assert c == expected['c']
    assert d == expected['d']


def test_index_access():
    expected = dict(a=1, b='b', c=False, d=None)
    data = ResultSet(expected.items())
    a = data[0]
    b = data[1]
    c = data[2]
    d = data[3]
    assert a == expected['a']
    assert b == expected['b']
    assert c == expected['c']
    assert d == expected['d']


def test_contains():
    expected = dict(a=1, b='b', c=False, d=None)
    data = ResultSet(expected.items())
    for v in expected.values():
        assert v in data


def test_str_repr():
    expected = dict(a=1, b='b', c=False, d=None)
    data = ResultSet(expected.items())
    assert data.__str__() == expected.__str__()
    assert data.__repr__() == expected.__repr__()


def test_type():
    c = ResultSetCursor.dict_type
    assert c == ResultSet
