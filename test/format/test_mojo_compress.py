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

from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest

from austin.events import AustinFrame
from austin.events import AustinMetadata
from austin.events import AustinMetrics
from austin.events import AustinSample
from austin.format.mojo import MojoStreamReader
from austin.format.mojo import MojoStreamWriter
from austin.format.mojo_compress import compress
from austin.format.mojo_compress import main


def make_mojo(events: list) -> BytesIO:
    buf = BytesIO()
    writer = MojoStreamWriter(buf)
    for event in events:
        writer.write(event)
    buf.seek(0)
    return buf


FRAME_A = AustinFrame(
    filename="mod.py", function="foo", line=1, line_end=0, column=0, column_end=0
)
FRAME_B = AustinFrame(
    filename="mod.py", function="bar", line=2, line_end=0, column=0, column_end=0
)


def read_events(buf: BytesIO) -> list:
    buf.seek(0)
    return list(MojoStreamReader(buf))


def test_compress_reduces_sample_count(datapath: Path):
    with (datapath / "test.mojo").open("rb") as f:
        out = BytesIO()
        compress(f, out)

    out.seek(0)
    reader = MojoStreamReader(out)
    reader.unwind()
    assert len(reader.samples) < 13227


def test_compress_preserves_metadata(datapath: Path):
    with (datapath / "test.mojo").open("rb") as f:
        out = BytesIO()
        compress(f, out)

    out.seek(0)
    reader = MojoStreamReader(out)
    reader.unwind()
    assert reader.metadata["mode"] == "wall"


def test_compress_aggregates_time():
    src = make_mojo(
        [
            AustinMetadata("mode", "wall"),
            AustinSample(
                pid=1,
                iid=0,
                thread="T1",
                metrics=AustinMetrics(time=100),
                frames=(FRAME_A,),
                gc=None,
                idle=None,
            ),
            AustinSample(
                pid=1,
                iid=0,
                thread="T1",
                metrics=AustinMetrics(time=200),
                frames=(FRAME_A,),
                gc=None,
                idle=None,
            ),
            AustinSample(
                pid=1,
                iid=0,
                thread="T1",
                metrics=AustinMetrics(time=50),
                frames=(FRAME_B,),
                gc=None,
                idle=None,
            ),
        ]
    )

    out = BytesIO()
    compress(src, out)

    events = read_events(out)
    samples = [e for e in events if isinstance(e, AustinSample)]

    assert len(samples) == 2
    by_frame = {s.frames[0].function: s for s in samples}
    assert by_frame["foo"].metrics.time == 300
    assert by_frame["bar"].metrics.time == 50


def test_compress_aggregates_memory():
    src = make_mojo(
        [
            AustinMetadata("mode", "memory"),
            AustinSample(
                pid=1,
                iid=0,
                thread="T1",
                metrics=AustinMetrics(memory=1024),
                frames=(FRAME_A,),
                gc=None,
                idle=None,
            ),
            AustinSample(
                pid=1,
                iid=0,
                thread="T1",
                metrics=AustinMetrics(memory=512),
                frames=(FRAME_A,),
                gc=None,
                idle=None,
            ),
        ]
    )

    out = BytesIO()
    compress(src, out)

    samples = [e for e in read_events(out) if isinstance(e, AustinSample)]
    assert len(samples) == 1
    assert samples[0].metrics.memory == 1536
    assert samples[0].metrics.time is None


def test_compress_aggregates_full_mode():
    src = make_mojo(
        [
            AustinMetadata("mode", "full"),
            AustinSample(
                pid=1,
                iid=0,
                thread="T1",
                metrics=AustinMetrics(time=100, memory=512),
                frames=(FRAME_A,),
                gc=False,
                idle=False,
            ),
            AustinSample(
                pid=1,
                iid=0,
                thread="T1",
                metrics=AustinMetrics(time=200, memory=256),
                frames=(FRAME_A,),
                gc=False,
                idle=False,
            ),
        ]
    )

    out = BytesIO()
    compress(src, out)

    samples = [e for e in read_events(out) if isinstance(e, AustinSample)]
    assert len(samples) == 1
    assert samples[0].metrics.time == 300
    assert samples[0].metrics.memory == 768


def test_compress_keeps_gc_and_idle_separate():
    src = make_mojo(
        [
            AustinMetadata("mode", "full"),
            AustinMetadata("gc", "on"),
            AustinSample(
                pid=1,
                iid=0,
                thread="T1",
                metrics=AustinMetrics(time=100, memory=0),
                frames=(FRAME_A,),
                gc=False,
                idle=False,
            ),
            AustinSample(
                pid=1,
                iid=0,
                thread="T1",
                metrics=AustinMetrics(time=50, memory=0),
                frames=(FRAME_A,),
                gc=True,
                idle=False,
            ),
            AustinSample(
                pid=1,
                iid=0,
                thread="T1",
                metrics=AustinMetrics(time=75, memory=0),
                frames=(FRAME_A,),
                gc=False,
                idle=True,
            ),
        ]
    )

    out = BytesIO()
    compress(src, out)

    samples = [e for e in read_events(out) if isinstance(e, AustinSample)]
    assert len(samples) == 3
    by_flags = {(s.gc, s.idle): s for s in samples}
    assert by_flags[(False, False)].metrics.time == 100
    assert by_flags[(True, False)].metrics.time == 50
    assert by_flags[(False, True)].metrics.time == 75


def test_compress_keeps_threads_separate():
    src = make_mojo(
        [
            AustinMetadata("mode", "wall"),
            AustinSample(
                pid=1,
                iid=0,
                thread="T1",
                metrics=AustinMetrics(time=100),
                frames=(FRAME_A,),
                gc=None,
                idle=None,
            ),
            AustinSample(
                pid=1,
                iid=0,
                thread="T2",
                metrics=AustinMetrics(time=200),
                frames=(FRAME_A,),
                gc=None,
                idle=None,
            ),
        ]
    )

    out = BytesIO()
    compress(src, out)

    samples = [e for e in read_events(out) if isinstance(e, AustinSample)]
    assert len(samples) == 2


def test_compress_main(datapath: Path, tmp_path: Path):
    output = tmp_path / "compressed.mojo"
    with patch("sys.argv", ["mojo-compress", str(datapath / "test.mojo"), str(output)]):
        main()
    assert output.exists()
    assert output.stat().st_size > 0


def test_compress_main_inplace(datapath: Path, tmp_path: Path):
    import shutil

    copy = tmp_path / "test.mojo"
    shutil.copy(datapath / "test.mojo", copy)
    original_size = copy.stat().st_size

    with patch("sys.argv", ["mojo-compress", str(copy)]):
        main()

    assert copy.stat().st_size < original_size


def test_compress_main_missing_file(tmp_path: Path):
    missing = tmp_path / "nonexistent.mojo"
    output = tmp_path / "out.mojo"
    with patch("sys.argv", ["mojo-compress", str(missing), str(output)]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
