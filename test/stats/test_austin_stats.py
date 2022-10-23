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
from copy import deepcopy

from austin.stats import AustinStats
from austin.stats import AustinStatsType
from austin.stats import Frame
from austin.stats import FrameStats
from austin.stats import Metric
from austin.stats import MetricType
from austin.stats import ProcessStats
from austin.stats import Sample
from austin.stats import ThreadStats


DUMP_LOAD_SAMPLES = """# mode: wall

{}P42;T0x7f45645646;foo_module.py:foo:10 300
P42;T0x7f45645646;foo_module.py:foo:10;bar_sample.py:bar:20 1000
"""


def test_austin_stats_single_process():
    stats = AustinStats(stats_type=AustinStatsType.WALL)

    stats.update(
        Sample.parse("P42;T0x7f45645646;foo_module.py:foo:10 152", MetricType.TIME)[0]
    )
    assert stats == AustinStats(
        stats_type=AustinStatsType.WALL,
        processes={
            42: ProcessStats(
                pid=42,
                threads={
                    "0x7f45645646": ThreadStats(
                        label="0x7f45645646",
                        own=Metric(MetricType.TIME, 0),
                        total=Metric(MetricType.TIME, 152),
                        children={
                            Frame("foo", "foo_module.py", 10): FrameStats(
                                label=Frame("foo", "foo_module.py", 10),
                                own=Metric(MetricType.TIME, 152),
                                total=Metric(MetricType.TIME, 152),
                            )
                        },
                    )
                },
            )
        },
    )

    stats.update(Sample.parse("P42;T0x7f45645646 148", MetricType.TIME)[0])
    assert stats == AustinStats(
        stats_type=AustinStatsType.WALL,
        processes={
            42: ProcessStats(
                pid=42,
                threads={
                    "0x7f45645646": ThreadStats(
                        label="0x7f45645646",
                        total=Metric(MetricType.TIME, 300),
                        own=Metric(MetricType.TIME, 148),
                        children={
                            Frame("foo", "foo_module.py", 10): FrameStats(
                                label=Frame("foo", "foo_module.py", 10),
                                own=Metric(MetricType.TIME, 152),
                                total=Metric(MetricType.TIME, 152),
                            )
                        },
                    )
                },
            )
        },
    )

    stats.update(
        Sample.parse("P42;T0x7f45645646;foo_module.py:foo:10 100", MetricType.TIME)[0]
    )
    assert stats == AustinStats(
        stats_type=AustinStatsType.WALL,
        processes={
            42: ProcessStats(
                pid=42,
                threads={
                    "0x7f45645646": ThreadStats(
                        label="0x7f45645646",
                        total=Metric(MetricType.TIME, 400),
                        own=Metric(MetricType.TIME, 148),
                        children={
                            Frame("foo", "foo_module.py", 10): FrameStats(
                                label=Frame("foo", "foo_module.py", 10),
                                own=Metric(MetricType.TIME, 252),
                                total=Metric(MetricType.TIME, 252),
                            )
                        },
                    )
                },
            )
        },
    )

    stats.update(
        Sample.parse("P42;T0x7f45645646;foo_module.py:bar:35 400", MetricType.TIME)[0]
    )
    assert stats == AustinStats(
        stats_type=AustinStatsType.WALL,
        processes={
            42: ProcessStats(
                pid=42,
                threads={
                    "0x7f45645646": ThreadStats(
                        label="0x7f45645646",
                        total=Metric(MetricType.TIME, 800),
                        own=Metric(MetricType.TIME, 148),
                        children={
                            Frame("foo", "foo_module.py", 10): FrameStats(
                                label=Frame("foo", "foo_module.py", 10),
                                own=Metric(MetricType.TIME, 252),
                                total=Metric(MetricType.TIME, 252),
                            ),
                            Frame("bar", "foo_module.py", 35): FrameStats(
                                label=Frame("bar", "foo_module.py", 35),
                                own=Metric(MetricType.TIME, 400),
                                total=Metric(MetricType.TIME, 400),
                            ),
                        },
                    )
                },
            )
        },
    )

    stats.update(
        Sample.parse("P42;T0x7f45645664;foo_module.py:foo:10 152", MetricType.TIME)[0]
    )
    assert stats == AustinStats(
        stats_type=AustinStatsType.WALL,
        processes={
            42: ProcessStats(
                pid=42,
                threads={
                    "0x7f45645664": ThreadStats(
                        label="0x7f45645664",
                        own=Metric(MetricType.TIME, 0),
                        total=Metric(MetricType.TIME, 152),
                        children={
                            Frame("foo", "foo_module.py", 10): FrameStats(
                                label=Frame("foo", "foo_module.py", 10),
                                own=Metric(MetricType.TIME, 152),
                                total=Metric(MetricType.TIME, 152),
                            )
                        },
                    ),
                    "0x7f45645646": ThreadStats(
                        label="0x7f45645646",
                        total=Metric(MetricType.TIME, 800),
                        own=Metric(MetricType.TIME, 148),
                        children={
                            Frame("foo", "foo_module.py", 10): FrameStats(
                                label=Frame("foo", "foo_module.py", 10),
                                own=Metric(MetricType.TIME, 252),
                                total=Metric(MetricType.TIME, 252),
                            ),
                            Frame("bar", "foo_module.py", 35): FrameStats(
                                label=Frame("bar", "foo_module.py", 35),
                                own=Metric(MetricType.TIME, 400),
                                total=Metric(MetricType.TIME, 400),
                            ),
                        },
                    ),
                },
            )
        },
    )


def test_dump():
    stats = AustinStats(AustinStatsType.WALL)

    EMPTY_SAMPLE = "P42;T0x7f45645646 1"
    FOO_SAMPLE = "P42;T0x7f45645646;foo_module.py:foo:10 150"
    BAR_SAMPLE = "P42;T0x7f45645646;foo_module.py:foo:10;bar_sample.py:bar:20 1000"

    stats.update(Sample.parse(FOO_SAMPLE, MetricType.TIME)[0])
    stats.update(Sample.parse(FOO_SAMPLE, MetricType.TIME)[0])
    stats.update(Sample.parse(BAR_SAMPLE, MetricType.TIME)[0])
    stats.update(Sample.parse(EMPTY_SAMPLE, MetricType.TIME)[0])

    buffer = io.StringIO()
    stats.dump(buffer)
    assert buffer.getvalue() == DUMP_LOAD_SAMPLES.format("P42;T0x7f45645646 1\n")


def test_load():
    buffer = io.StringIO(DUMP_LOAD_SAMPLES.format(""))
    stats = AustinStats.load(buffer)
    assert stats[AustinStatsType.WALL] == AustinStats(
        stats_type=AustinStatsType.WALL,
        processes={
            42: ProcessStats(
                pid=42,
                threads={
                    "0x7f45645646": ThreadStats(
                        label="0x7f45645646",
                        own=Metric(MetricType.TIME, 0),
                        total=Metric(MetricType.TIME, 1300),
                        children={
                            Frame(
                                function="foo", filename="foo_module.py", line=10
                            ): FrameStats(
                                label=Frame(
                                    function="foo", filename="foo_module.py", line=10
                                ),
                                own=Metric(MetricType.TIME, 300),
                                total=Metric(MetricType.TIME, 1300),
                                children={
                                    Frame(
                                        function="bar",
                                        filename="bar_sample.py",
                                        line=20,
                                    ): FrameStats(
                                        label=Frame(
                                            function="bar",
                                            filename="bar_sample.py",
                                            line=20,
                                        ),
                                        own=Metric(MetricType.TIME, 1000),
                                        total=Metric(MetricType.TIME, 1000),
                                        children={},
                                        height=1,
                                    )
                                },
                                height=0,
                            )
                        },
                    )
                },
            )
        },
    )


def test_deepcopy():
    stats = AustinStats(stats_type=AustinStatsType.WALL)

    stats.update(
        Sample.parse("P42;T0x7f45645646;foo_module.py:foo:10 152", MetricType.TIME)[0]
    )
    cloned_stats = deepcopy(stats)
    assert cloned_stats == stats
    assert cloned_stats is not stats
