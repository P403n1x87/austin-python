# This file is part of "austin-python" which is released under GPL.
#
# See file LICENCE or go to http://www.gnu.org/licenses/ for full license
# details.
#
# austin-python is a Python wrapper around Austin, the CPython frame stack
# sampler.
#
# Copyright (c) 2018-2026 Gabriele N. Tornetta <phoenix1987@gmail.com>.
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pathlib import Path
import time

import pytest

from austin.events import AustinSample
from austin.format import file_progress
from austin.format import open_profile
from austin.format.collapsed_stack import AustinFileReader
from austin.format.mojo import MojoStreamReader


@pytest.mark.parametrize(
    "name,reader", [("test.mojo", MojoStreamReader), ("test.austin", AustinFileReader)]
)
def test_open_profile_detects_format(datapath: Path, name, reader):
    with open_profile(datapath / name) as events:
        assert isinstance(events, reader)
        assert any(isinstance(e, AustinSample) for e in events)


@pytest.mark.parametrize("name", ["test.mojo", "test.austin"])
def test_open_profile_progress(datapath: Path, name):
    fractions: list[float] = []

    with open_profile(datapath / name, fractions.append) as events:
        for _ in events:
            pass

    assert fractions[-1] == 1.0
    assert fractions == sorted(fractions)


def test_file_progress_interval(tmp_path: Path):
    path = tmp_path / "data"
    path.write_bytes(b"x" * 100)
    fractions: list[float] = []

    with path.open("rb") as f, file_progress(f, fractions.append, interval=0.01):
        f.raw.read(50)
        time.sleep(0.1)

    assert 0.5 in fractions and fractions[-1] == 1.0
