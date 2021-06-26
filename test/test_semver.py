import pytest

from austin import _to_semver


@pytest.mark.parametrize(
    ("version", "semver"),
    [
        ("3.0.0", (3, 0, 0)),
        ("3.0", (3, 0, 0)),
        ("3", (3, 0, 0)),
        ("3.0.0a1", (3, 0, 0)),
        ("0.1.0", (0, 1, 0)),
        ("3.9.?", (3, 9, 0)),
    ],
)
def test_semver(version, semver):
    assert _to_semver(version) == semver
