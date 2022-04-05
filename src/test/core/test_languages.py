def test_finnish():
    """Just makes sure this works
    """
    from pycountry import languages

    assert languages.lookup("fi").alpha_3 == "fin"
    assert languages.lookup("fi").alpha_2 == "fi"
