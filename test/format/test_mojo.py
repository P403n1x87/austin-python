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

from austin.events import AustinFrame
from austin.events import AustinMetadata
from austin.events import AustinMetrics
from austin.events import AustinSample
from austin.format.collapsed_stack import main
from austin.format.mojo import MojoFrame
from austin.format.mojo import MojoMetadata
from austin.format.mojo import MojoStreamReader
from austin.format.mojo import MojoStreamWriter
from austin.format.mojo import MojoString
from austin.format.mojo import to_varint
from austin.tools.mojodbg import mojodbg


HERE = Path(__file__).parent
DATA = HERE.parent / "data"


@pytest.mark.parametrize("case", ["test", "mp"])
def test_mojo_snapshot(case):
    input = (DATA / case).with_suffix(".mojo")
    output = Path(tempfile.NamedTemporaryFile().name).with_suffix(".austin")
    expected = (DATA / case).with_suffix(".austin")

    sys.argv = ["mojo2austin", str(input), str(output)]

    main()

    if not expected.exists():
        expected.write_text(output.read_text())
        raise AssertionError("Expected file does not exist. Created it.")

    assert expected.read_text()[:128] == output.read_text()[:128]


def test_mojo_varint():
    for _ in range(100_000):
        n = randint(int(-4e9), int(4e9))
        buffer = BytesIO()
        buffer.write(to_varint(n))
        buffer.seek(0)
        assert MojoStreamReader(buffer).read_int() == n


def test_mojo_column_info():
    with (DATA / "column.mojo").open("rb") as stream:
        frames = {
            _
            for _ in MojoStreamReader(stream).parse()
            if isinstance(_, MojoFrame) and _.filename.value == "/tmp/column.py"
        }
        assert frames == {
            MojoFrame(
                key=1289736945696,
                filename=MojoString(key=20271280, value="/tmp/column.py"),
                scope=MojoString(key=28930616, value="<module>"),
                line=15,
                line_end=18,
                column=5,
                column_end=2,
            ),
            MojoFrame(
                key=1293162643485,
                filename=MojoString(key=20271280, value="/tmp/column.py"),
                scope=MojoString(key=20364976, value="lazy"),
                line=5,
                line_end=5,
                column=9,
                column_end=19,
            ),
            MojoFrame(
                key=1293180469286,
                filename=MojoString(key=20271280, value="/tmp/column.py"),
                scope=MojoString(key=20357744, value="fib"),
                line=11,
                line_end=13,
                column=5,
                column_end=24,
            ),
            MojoFrame(
                key=1276044640259,
                filename=MojoString(key=20271280, value="/tmp/column.py"),
                scope=MojoString(key=28930552, value="<listcomp>"),
                line=15,
                line_end=18,
                column=5,
                column_end=2,
            ),
            MojoFrame(
                key=1289736945703,
                filename=MojoString(key=20271280, value="/tmp/column.py"),
                scope=MojoString(key=28930616, value="<module>"),
                line=20,
                line_end=20,
                column=1,
                column_end=9,
            ),
            MojoFrame(
                key=1293162643483,
                filename=MojoString(key=20271280, value="/tmp/column.py"),
                scope=MojoString(key=20364976, value="lazy"),
                line=5,
                line_end=5,
                column=9,
                column_end=19,
            ),
            MojoFrame(
                key=1276044640281,
                filename=MojoString(key=20271280, value="/tmp/column.py"),
                scope=MojoString(key=28930552, value="<listcomp>"),
                line=16,
                line_end=16,
                column=5,
                column_end=17,
            ),
        }


def test_mojo_data():
    input = (DATA / "test").with_suffix(".mojo")

    with input.open("rb") as stream:
        m = MojoStreamReader(stream)
        m.unwind()

        assert m.metadata == {
            "austin": "3.4.0",
            "duration": "1038089",
            "interval": "100",
            "mode": "wall",
        }

        n_samples = len(m.samples)
        assert n_samples == 13227


def test_mojo_writer():
    buffer = BytesIO()
    mojo_writer = MojoStreamWriter(buffer)

    mojo_writer.write(original_meta := AustinMetadata("mode", "wall"))
    for sample in (
        original_samples := [
            AustinSample(
                pid=42,
                iid=0,
                thread="0x7f45645646",
                metrics=AustinMetrics(time=1, memory=None),
                frames=None,
                gc=None,
                idle=None,
            ),
            AustinSample(
                pid=42,
                iid=0,
                thread="0x7f45645646",
                metrics=AustinMetrics(time=300, memory=None),
                frames=(
                    AustinFrame(
                        filename="foo_module.py",
                        function="foo",
                        line=10,
                        line_end=0,
                        column=0,
                        column_end=0,
                    ),
                ),
                gc=None,
                idle=None,
            ),
            AustinSample(
                pid=42,
                iid=0,
                thread="0x7f45645646",
                metrics=AustinMetrics(time=1000, memory=None),
                frames=(
                    AustinFrame(
                        filename="foo_module.py",
                        function="foo",
                        line=10,
                        line_end=0,
                        column=0,
                        column_end=0,
                    ),
                    AustinFrame(
                        filename="bar_sample.py",
                        function="bar",
                        line=20,
                        line_end=0,
                        column=0,
                        column_end=0,
                    ),
                ),
                gc=None,
                idle=None,
            ),
        ]
    ):
        mojo_writer.write(sample)

    buffer.seek(0)
    mojo_reader = MojoStreamReader(buffer)

    meta, *samples = mojo_reader

    assert meta == original_meta
    assert samples == original_samples
