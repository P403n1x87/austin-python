from austin.tools.diff import diff


def test_diff():
    with open("test/data/diff_a.austin") as a, open(
        "test/data/diff_b.austin"
    ) as b, open("test/data/diff_a-b.austin") as d:
        assert diff(a, b).strip() == d.read().strip()
