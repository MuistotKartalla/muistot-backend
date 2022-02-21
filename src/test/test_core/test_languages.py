def test_finnish():
    from languager import get_language

    assert get_language("fi").code == "fin"
