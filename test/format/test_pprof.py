# This file is part of "austin-python" which is released under GPL.
#
# See file LICENCE or go to http://www.gnu.org/licenses/ for full license
# details.
#
# austin-python is a Python wrapper around Austin, the CPython frame stack
# sampler.
#
# Copyright (c) 2018-2020 Gabriele N. Tornetta <phoenix1987@gmail.com>.
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

import io
from pathlib import Path
import sys

from austin.events import AustinMetadata
from austin.events import AustinSample
from austin.format import open_profile
from austin.format.collapsed_stack import AustinFileReader
from austin.format.pprof import PProf
from austin.format.pprof.__main__ import main
from austin.format.pprof.profile import Sample


def test_pprof(datapath: Path):
    prof = None

    with AustinFileReader((datapath / "austin.out").open()) as austin:
        for e in austin:
            # We need to determine the mode before we can start adding samples
            # to the pprof
            if isinstance(e, AustinMetadata) and e.name == "mode":
                prof = PProf(e.value)
                break
        else:
            raise RuntimeError("No mode metadata found in Austin file")

        for e in austin:
            if not isinstance(e, AustinSample):
                continue

            prof.add_sample(e)

        bstream = io.BytesIO()
        prof.dump(bstream)

        with open(datapath / "austin.pprof", "rb") as pprof:
            assert pprof.read() == bstream.getvalue()


def test_pprof_negative_varint():
    # Negative int64 values are encoded as 10-byte two's complement varints
    assert Sample(value=[-1]).SerializeToString() == b"\x12\x0a" + b"\xff" * 9 + b"\x01"


def test_pprof_main_mojo(datapath: Path, tmp_path: Path, monkeypatch):
    # Austin 4 emits MOJO by default, so the converter must accept it
    output = tmp_path / "test.pprof"
    monkeypatch.setattr(
        sys, "argv", ["austin2pprof", str(datapath / "test.mojo"), str(output)]
    )

    main()

    # Converting the same profile through the collapsed stack format must give
    # the same result.
    with open_profile(datapath / "test.mojo") as events:
        prof = None
        for e in events:
            if isinstance(e, AustinMetadata) and e.name == "mode":
                prof = PProf(e.value)
            elif isinstance(e, AustinSample):
                assert prof is not None
                prof.add_sample(e)

    assert prof is not None
    bstream = io.BytesIO()
    prof.dump(bstream)
    assert output.read_bytes() == bstream.getvalue()
