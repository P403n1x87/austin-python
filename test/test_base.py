from pytest import raises

from austin.base import AustinState
from austin.errors import AustinError
from austin.simple import SimpleAustin


class _SimpleAustin(SimpleAustin):
    def on_sample(self, sample):
        pass


def test_is_running_initially_false():
    austin = _SimpleAustin()
    assert not austin.is_running()


def test_get_arguments_initially_none():
    austin = _SimpleAustin()
    assert austin.get_arguments() is None


def test_state_initially_not_started():
    austin = _SimpleAustin()
    assert austin.state is AustinState.NOT_STARTED


def test_check_version_too_old():
    austin = _SimpleAustin()
    austin._meta["austin"] = "3.9.0"
    with raises(AustinError, match="Incompatible Austin version"):
        austin._check_version()


def test_check_version_none():
    austin = _SimpleAustin()
    # _meta has no "austin" key → version returns (0, 0, 0) < minimum
    with raises(AustinError):
        austin._check_version()
