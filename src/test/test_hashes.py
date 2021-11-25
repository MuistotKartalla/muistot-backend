from app.security import hashes


def test_good():
    plain, checksum = hashes.generate()
    assert hashes.validate(plain.split(':')[0], checksum)


def test_bad_checksum():
    plain, _ = hashes.generate()
    assert not hashes.validate(plain, plain)


def test_bad_plain():
    plain, checksum = hashes.generate()
    assert not hashes.validate(checksum, checksum)


def test_bad_time():
    import base64
    plain, checksum = hashes.generate()
    p2 = base64.standard_b64decode(plain.split(':')[0])[:-1]
    p2 = base64.standard_b64encode(p2).decode('ascii')
    assert not hashes.validate(
        f"{p2}:{plain.split(':')[1]}",
        checksum
    )
