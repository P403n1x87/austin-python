import pathlib

import pytest


DATAPATH = pathlib.Path(__file__).parent / "data"


@pytest.fixture()
def datapath() -> pathlib.Path:
    return DATAPATH
