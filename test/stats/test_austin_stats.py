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

from austin.events import AustinFrame
from austin.events import AustinMetadata
from austin.events import AustinMetrics
from austin.events import AustinSample
from austin.format.collapsed_stack import AustinFileReader
from austin.format.collapsed_stack import parse_collapsed_stack
from austin.stats import AustinStats
from austin.stats import AustinStatsType
from austin.stats import FrameStats
from austin.stats import ProcessStats
from austin.stats import ThreadInfo
from austin.stats import ThreadStats

DUMP_LOAD_SAMPLES = """# mode: wall

{}P42;T0x7f45645646;foo_module.py:foo:10 300
P42;T0x7f45645646;foo_module.py:foo:10;bar_sample.py:bar:20 1000
"""


def test_austin_stats_single_process():
    stats = AustinStats(stats_type=AustinStatsType.WALL)

    stats.update(parse_collapsed_stack("P42;T0x7f45645646;foo_module.py:foo:10 152"))
    assert stats == AustinStats(
        stats_type=AustinStatsType.WALL,
        processes={
            42: ProcessStats(
                pid=42,
                threads={
                    ThreadInfo("0x7f45645646", 0): ThreadStats(
                        label=ThreadInfo("0x7f45645646", 0),
                        own=0,
                        total=152,
                        samples=1,
                        children={
                            AustinFrame(
                                function="foo", filename="foo_module.py", line=10
                            ): FrameStats(
                                label=AustinFrame(
                                    function="foo", filename="foo_module.py", line=10
                                ),
                                own=152,
                                total=152,
                                samples=1,
                            )
                        },
                    )
                },
            )
        },
    )

    stats.update(parse_collapsed_stack("P42;T0x7f45645646 148"))
    assert stats == AustinStats(
        stats_type=AustinStatsType.WALL,
        processes={
            42: ProcessStats(
                pid=42,
                threads={
                    ThreadInfo("0x7f45645646", 0): ThreadStats(
                        label=ThreadInfo("0x7f45645646", 0),
                        total=300,
                        samples=2,
                        own=148,
                        children={
                            AustinFrame(
                                function="foo", filename="foo_module.py", line=10
                            ): FrameStats(
                                label=AustinFrame(
                                    function="foo", filename="foo_module.py", line=10
                                ),
                                own=152,
                                total=152,
                                samples=1,
                            )
                        },
                    )
                },
            )
        },
    )

    stats.update(parse_collapsed_stack("P42;T0x7f45645646;foo_module.py:foo:10 100"))
    assert stats == AustinStats(
        stats_type=AustinStatsType.WALL,
        processes={
            42: ProcessStats(
                pid=42,
                threads={
                    ThreadInfo("0x7f45645646", 0): ThreadStats(
                        label=ThreadInfo("0x7f45645646", 0),
                        total=400,
                        samples=3,
                        own=148,
                        children={
                            AustinFrame(
                                function="foo", filename="foo_module.py", line=10
                            ): FrameStats(
                                label=AustinFrame(
                                    function="foo", filename="foo_module.py", line=10
                                ),
                                own=252,
                                total=252,
                                samples=2,
                            )
                        },
                    )
                },
            )
        },
    )

    stats.update(parse_collapsed_stack("P42;T0x7f45645646;foo_module.py:bar:35 400"))
    assert stats == AustinStats(
        stats_type=AustinStatsType.WALL,
        processes={
            42: ProcessStats(
                pid=42,
                threads={
                    ThreadInfo("0x7f45645646", 0): ThreadStats(
                        label=ThreadInfo("0x7f45645646", 0),
                        total=800,
                        samples=4,
                        own=148,
                        children={
                            AustinFrame(
                                function="foo", filename="foo_module.py", line=10
                            ): FrameStats(
                                label=AustinFrame(
                                    function="foo", filename="foo_module.py", line=10
                                ),
                                own=252,
                                total=252,
                                samples=2,
                            ),
                            AustinFrame(
                                function="bar", filename="foo_module.py", line=35
                            ): FrameStats(
                                label=AustinFrame(
                                    function="bar", filename="foo_module.py", line=35
                                ),
                                own=400,
                                total=400,
                                samples=1,
                            ),
                        },
                    )
                },
            )
        },
    )

    stats.update(parse_collapsed_stack("P42;T0x7f45645664;foo_module.py:foo:10 152"))
    assert stats == AustinStats(
        stats_type=AustinStatsType.WALL,
        processes={
            42: ProcessStats(
                pid=42,
                threads={
                    ThreadInfo("0x7f45645664", 0): ThreadStats(
                        label=ThreadInfo("0x7f45645664", 0),
                        own=0,
                        total=152,
                        samples=1,
                        children={
                            AustinFrame(
                                function="foo", filename="foo_module.py", line=10
                            ): FrameStats(
                                label=AustinFrame(
                                    function="foo", filename="foo_module.py", line=10
                                ),
                                own=152,
                                total=152,
                                samples=1,
                            )
                        },
                    ),
                    ThreadInfo("0x7f45645646", 0): ThreadStats(
                        label=ThreadInfo("0x7f45645646", 0),
                        total=800,
                        samples=4,
                        own=148,
                        children={
                            AustinFrame(
                                function="foo", filename="foo_module.py", line=10
                            ): FrameStats(
                                label=AustinFrame(
                                    function="foo", filename="foo_module.py", line=10
                                ),
                                own=252,
                                total=252,
                                samples=2,
                            ),
                            AustinFrame(
                                function="bar", filename="foo_module.py", line=35
                            ): FrameStats(
                                label=AustinFrame(
                                    function="bar", filename="foo_module.py", line=35
                                ),
                                own=400,
                                total=400,
                                samples=1,
                            ),
                        },
                    ),
                },
            )
        },
    )


def test_flatten():
    stats = AustinStats(AustinStatsType.WALL)

    EMPTY_SAMPLE = "P42;T0x7f45645646 1"
    FOO_SAMPLE = "P42;T0x7f45645646;foo_module.py:foo:10 150"
    BAR_SAMPLE = "P42;T0x7f45645646;foo_module.py:foo:10;bar_sample.py:bar:20 1000"

    stats.update(parse_collapsed_stack(FOO_SAMPLE))
    stats.update(parse_collapsed_stack(FOO_SAMPLE))
    stats.update(parse_collapsed_stack(BAR_SAMPLE))
    stats.update(parse_collapsed_stack(EMPTY_SAMPLE))

    events = list(stats.flatten())

    assert events == [
        AustinSample(
            pid=42,
            iid=0,
            thread="0x7f45645646",
            metrics=AustinMetrics(time=1, memory=None),
            frames=(),
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
                    line_end=None,
                    column=None,
                    column_end=None,
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
                    line_end=None,
                    column=None,
                    column_end=None,
                ),
                AustinFrame(
                    filename="bar_sample.py",
                    function="bar",
                    line=20,
                    line_end=None,
                    column=None,
                    column_end=None,
                ),
            ),
            gc=None,
            idle=None,
        ),
    ]


def test_load():
    buffer = io.StringIO(DUMP_LOAD_SAMPLES.format(""))
    stats = AustinStats.load(AustinFileReader(buffer))
    assert stats[AustinStatsType.WALL] == AustinStats(
        stats_type=AustinStatsType.WALL,
        processes={
            42: ProcessStats(
                pid=42,
                threads={
                    ThreadInfo("0x7f45645646", 0): ThreadStats(
                        label=ThreadInfo("0x7f45645646", 0),
                        own=0,
                        total=1300,
                        samples=2,
                        children={
                            AustinFrame(
                                function="foo", filename="foo_module.py", line=10
                            ): FrameStats(
                                label=AustinFrame(
                                    function="foo", filename="foo_module.py", line=10
                                ),
                                own=300,
                                total=1300,
                                samples=2,
                                children={
                                    AustinFrame(
                                        function="bar",
                                        filename="bar_sample.py",
                                        line=20,
                                    ): FrameStats(
                                        label=AustinFrame(
                                            function="bar",
                                            filename="bar_sample.py",
                                            line=20,
                                        ),
                                        own=1000,
                                        total=1000,
                                        samples=1,
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

    stats.update(parse_collapsed_stack("P42;T0x7f45645646;foo_module.py:foo:10 152"))
    cloned_stats = deepcopy(stats)
    assert cloned_stats == stats
    assert cloned_stats is not stats


def test_load_full_mode_cpu_excludes_idle():
    frames = (AustinFrame("foo_module.py", "foo", 10),)
    stats = AustinStats.load(
        iter(
            [
                AustinMetadata("mode", "full"),
                AustinSample(
                    pid=42,
                    iid=0,
                    thread="0x7f45645646",
                    metrics=AustinMetrics(time=100, memory=10),
                    frames=frames,
                    idle=False,
                ),
                AustinSample(
                    pid=42,
                    iid=0,
                    thread="0x7f45645646",
                    metrics=AustinMetrics(time=900, memory=-5),
                    frames=frames,
                    idle=True,
                ),
            ]
        )
    )

    def total(stats_type: AustinStatsType) -> int:
        thread_info = ThreadInfo("0x7f45645646", 0)
        return stats[stats_type].processes[42].threads[thread_info].total

    assert total(AustinStatsType.CPU) == 100
    assert total(AustinStatsType.WALL) == 1000
    assert total(AustinStatsType.MEMORY_ALLOC) == 10
    assert total(AustinStatsType.MEMORY_DEALLOC) == 5
