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
from pathlib import Path

import pytest

from austin.tools.resolve import main


HERE = Path(__file__).parent
DATA = HERE.parent / "data"


@pytest.mark.xfail(reason="Dependant on binaries being available")
@pytest.mark.skipif(sys.platform != "linux", reason="Only supported on Linux")
def test_resolve_snapshot():
    input = DATA / "austinp.mojo"
    output = Path(tempfile.NamedTemporaryFile().name).with_suffix(".resolved.mojo")
    expected = DATA / "austinp.resolved.mojo"

    sys.argv = ["austinp-resolve", str(input), str(output)]

    main()

    assert expected.read_bytes() == output.read_bytes()
