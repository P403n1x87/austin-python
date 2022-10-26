# This file is part of "austin-python" which is released under GPL.
#
# See file LICENCE or go to http://www.gnu.org/licenses/ for full license
# details.
#
# austin-python is a Python wrapper around Austin, the CPython frame stack
# sampler.
#
# Copyright (c) 2018-2022 Gabriele N. Tornetta <phoenix1987@gmail.com>.
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

import sys
import tempfile
from io import BytesIO
from pathlib import Path
from random import randint

import pytest

from austin.format.mojo import MojoFile
from austin.format.mojo import main
from austin.format.mojo import to_varint


HERE = Path(__file__).parent
DATA = HERE.parent / "data"


@pytest.mark.parametrize("case", ["test", "mp"])
def test_mojo_snapshot(case):
    input = (DATA / case).with_suffix(".mojo")
    output = Path(tempfile.NamedTemporaryFile().name).with_suffix(".austin")
    expected = (DATA / case).with_suffix(".austin")

    sys.argv = ["mojo2austin", str(input), str(output)]

    main()

    assert expected.read_text() == output.read_text()


def test_mojo_varint():
    for _ in range(100_000):
        n = randint(-4e9, 4e9)
        buffer = BytesIO()
        buffer.write(b"MOJ\0" + to_varint(n))
        buffer.seek(0)
        assert MojoFile(buffer).read_int() == n
