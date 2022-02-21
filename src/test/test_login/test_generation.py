def make_stats(_):
    from muistoja.login.logic.namegen import generate
    from collections import Counter

    generated = []
    for i in range(0, 100000):
        generated.append(generate())
    return Counter(generated).most_common(1)[0][1] < 5


def test_gen():
    from multiprocessing import Pool

    with Pool() as p:
        result = p.map(make_stats, range(0, 100))
    assert all(result)
