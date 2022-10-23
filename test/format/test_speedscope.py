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
from dataclasses import fields

from austin.format import Mode
from austin.format.speedscope import Speedscope
from austin.format.speedscope import SpeedscopeFrame
from austin.format.speedscope import SpeedscopeProfile
from austin.stats import AustinFileReader
from austin.stats import InvalidSample
from austin.stats import MetricType
from austin.stats import Sample


_SPEEDSCOPE_FILE_FIELDS = ("$schema", "shared", "profiles", "name", "exporter")
_SPEEDSCOPE_SCHEMA_URL = "https://www.speedscope.app/file-format-schema.json"
_SPEEDSCOPE_FRAME_FIELDS = tuple([field.name for field in fields(SpeedscopeFrame)])
_SPEEDSCOPE_PROFILE_FIELDS = tuple([field.name for field in fields(SpeedscopeProfile)])


def test_speedscope_full_metrics_idle():
    speedscope = Speedscope("austin_full_metrics", "full")

    # The format for each line of this array can be found in
    # austin.stats.Sample.parse.
    for sample in [
        "P42;T123;foo_module.py:foo:10 10,1,-30",
        "P42;T123;foo_module.py:foo:10 10,1,20",
    ]:
        speedscope.add_samples(Sample.parse(sample))

    speedscope_data = speedscope.asdict()
    for file_field in _SPEEDSCOPE_FILE_FIELDS:
        assert file_field in speedscope_data

    assert speedscope_data["$schema"] == _SPEEDSCOPE_SCHEMA_URL
    assert speedscope_data["name"] == "austin_full_metrics"
    assert "Austin2Speedscope Converter" in speedscope_data["exporter"]

    sframe_list = speedscope_data["shared"]["frames"]
    assert len(sframe_list) == 1
    for sframe in sframe_list:
        for field in _SPEEDSCOPE_FRAME_FIELDS:
            assert field in sframe

    assert sframe_list[0]["name"] == "foo"
    assert sframe_list[0]["file"] == "foo_module.py"
    assert sframe_list[0]["line"] == 10

    sprofile_list = speedscope_data["profiles"]
    assert len(sprofile_list) == 3
    for sprofile in sprofile_list:
        for field in _SPEEDSCOPE_PROFILE_FIELDS:
            assert field in sprofile
        assert sprofile["type"] == "sampled"
        assert sprofile["startValue"] == 0

    # The sort in SpeedscopeProfile.asdict() returns profiles in insertion
    # order because the keys for all profiles are the same: "42:123",
    # which refers to the process ID and thread ID, respectively. The
    # part of each line that controls insertion order in this particular
    # data set is the triple of numbers at the end of each line, which
    # is passed to austin.stats.Metric.parse. For consistency,
    # the entries of this triple will be referred to positionally using
    # Python indexing conventions.
    #
    # Data from this triple is passed into a four element list of
    # metrics as follows:
    #
    # metric[0] is CPU time; it is zero if triple[1] is nonzero, otherwise
    # it equals triple[0]
    #
    # metric[1] is wall clock time; it equals triple[0]
    #
    # metric[2] is memory allocation in bytes; it equals triple[2] if
    # triple[2] > 0, otherwise it equals zero
    #
    # matric[3] is memory deallocation  in bytes; it equals -triple[2]
    # if triple[2] < 0, otherwise it equals 0.
    #
    # Insertions into weight arrays are attempted in the following
    # order: (CPU time, wall clock time, memory allocation, memory
    # deallocation). Insertion logic can be found in
    # austin.format.Speedscope.add_samples and
    # austin.format.Speedscope.get_profile.
    #
    # If the value of a particular metric is zero, then nothing is inserted.
    #
    # Consequently, the insertion order is as follows: wall clock
    # time, deallocation, allocation. Weight information is never
    # inserted into the CPU time profile weight arrays in this
    # test. Weight information is, however, inserted into the CPU time
    # profile weight array in the other test in this file.
    assert sprofile_list[0]["name"] == "Wall time profile for 42:123"
    assert sprofile_list[0]["endValue"] == 20
    assert sprofile_list[0]["unit"] == "microseconds"

    assert len(sprofile_list[0]["samples"]) == 2
    assert sprofile_list[0]["samples"] == [[0], [0]]
    assert len(sprofile_list[0]["weights"]) == 2
    assert sprofile_list[0]["weights"] == [10, 10]

    assert sprofile_list[1]["name"] == "Memory deallocation profile for 42:123"
    assert sprofile_list[1]["endValue"] == 30
    assert sprofile_list[1]["unit"] == "bytes"

    assert len(sprofile_list[1]["samples"]) == 1
    assert sprofile_list[1]["samples"] == [[0]]
    assert len(sprofile_list[1]["weights"]) == 1
    assert sprofile_list[1]["weights"] == [30]

    assert sprofile_list[2]["name"] == "Memory allocation profile for 42:123"
    assert sprofile_list[2]["endValue"] == 20
    assert sprofile_list[2]["unit"] == "bytes"

    assert len(sprofile_list[2]["samples"]) == 1
    assert sprofile_list[2]["samples"] == [[0]]
    assert len(sprofile_list[2]["weights"]) == 1
    assert sprofile_list[2]["weights"] == [20]


def test_speedscope_full_metrics():
    speedscope = Speedscope("austin_full_metrics", "full")
    for sample in [
        "P42;T123;foo_module.py:foo:10 10,0,-30",
        "P42;T123;foo_module.py:foo:10 10,1,20",
    ]:
        speedscope.add_samples(Sample.parse(sample))

    speedscope_data = speedscope.asdict()
    for file_field in _SPEEDSCOPE_FILE_FIELDS:
        assert file_field in speedscope_data

    assert speedscope_data["$schema"] == _SPEEDSCOPE_SCHEMA_URL
    assert speedscope_data["name"] == "austin_full_metrics"
    assert "Austin2Speedscope Converter" in speedscope_data["exporter"]

    sframe_list = speedscope_data["shared"]["frames"]
    assert len(sframe_list) == 1
    for sframe in sframe_list:
        for field in _SPEEDSCOPE_FRAME_FIELDS:
            assert field in sframe

    assert sframe_list[0]["name"] == "foo"
    assert sframe_list[0]["file"] == "foo_module.py"
    assert sframe_list[0]["line"] == 10

    sprofile_list = speedscope_data["profiles"]
    assert len(sprofile_list) == 4
    for sprofile in sprofile_list:
        for field in _SPEEDSCOPE_PROFILE_FIELDS:
            assert field in sprofile
        assert sprofile["type"] == "sampled"

    # See the comments in the test above for a discussion of why
    # Speedscope profiles appear in the order tested below.
    assert sprofile_list[0]["name"] == "CPU time profile for 42:123"
    assert sprofile_list[0]["endValue"] == 10
    assert sprofile_list[0]["unit"] == "microseconds"

    assert len(sprofile_list[0]["samples"]) == 1
    assert sprofile_list[0]["samples"] == [[0]]
    assert len(sprofile_list[0]["weights"]) == 1
    assert sprofile_list[0]["weights"] == [10]

    assert sprofile_list[1]["name"] == "Wall time profile for 42:123"
    assert sprofile_list[1]["endValue"] == 20
    assert sprofile_list[1]["unit"] == "microseconds"

    assert len(sprofile_list[1]["samples"]) == 2
    assert sprofile_list[1]["samples"] == [[0], [0]]
    assert len(sprofile_list[1]["weights"]) == 2
    assert sprofile_list[1]["weights"] == [10, 10]

    assert sprofile_list[2]["name"] == "Memory deallocation profile for 42:123"
    assert sprofile_list[2]["endValue"] == 30
    assert sprofile_list[2]["unit"] == "bytes"

    assert len(sprofile_list[2]["samples"]) == 1
    assert sprofile_list[2]["samples"] == [[0]]
    assert len(sprofile_list[2]["weights"]) == 1
    assert sprofile_list[2]["weights"] == [30]

    assert sprofile_list[3]["name"] == "Memory allocation profile for 42:123"
    assert sprofile_list[3]["endValue"] == 20
    assert sprofile_list[3]["unit"] == "bytes"

    assert len(sprofile_list[3]["samples"]) == 1
    assert sprofile_list[3]["samples"] == [[0]]
    assert len(sprofile_list[3]["weights"]) == 1
    assert sprofile_list[3]["weights"] == [20]


def test_speedscope_wall_metrics_only(datapath):
    with AustinFileReader(datapath / "austin.out") as austin:
        mode = austin.metadata["mode"]
        assert Mode.from_metadata(mode) == Mode.WALL

        speedscope = Speedscope("austin.out", mode, indent=2)

        for line in austin:
            try:
                speedscope.add_samples(Sample.parse(line, MetricType.from_mode(mode)))
            except InvalidSample:
                continue

        text_stream = io.StringIO()
        speedscope.dump(text_stream)

        with open(datapath / "austin.json", "r") as sprof:
            assert text_stream.getvalue() == sprof.read()
