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

from copy import deepcopy

from austin.stats import Frame
from austin.stats import FrameStats
from austin.stats import Metric
from austin.stats import MetricType


def test_frame_stats_add_disjoint():
    ref_frame_stats = FrameStats(
        label=Frame("foo", "foo_module.py", 10),
        own=Metric(MetricType.TIME, 10),
        total=Metric(MetricType.TIME, 20),
        height=0,
        children={
            Frame("foobar", "foo_module.py", 5): FrameStats(
                label=Frame("foobar", "foo_module.py", 5),
                own=Metric(MetricType.TIME, 10),
                total=Metric(MetricType.TIME, 10),
                height=1,
            )
        },
    )

    frame_stats = deepcopy(ref_frame_stats) << FrameStats(
        label=Frame("bar", "bar_module.py", 10),
        own=Metric(MetricType.TIME, 10),
        total=Metric(MetricType.TIME, 20),
        height=0,
        children={
            Frame("foobar", "bar_module.py", 5): FrameStats(
                label=Frame("foobar", "bar_module.py", 5),
                own=Metric(MetricType.TIME, 10),
                total=Metric(MetricType.TIME, 10),
                height=1,
            )
        },
    )

    assert frame_stats == ref_frame_stats


def test_frame_stats_add_matching():
    frame_stats = FrameStats(
        label=Frame("foo", "foo_module.py", 10),
        own=Metric(MetricType.TIME, 10),
        total=Metric(MetricType.TIME, 20),
        height=0,
        children={
            Frame("foobar", "foo_module.py", 5): FrameStats(
                label=Frame("foobar", "foo_module.py", 5),
                own=Metric(MetricType.TIME, 10),
                total=Metric(MetricType.TIME, 10),
                height=1,
            )
        },
    ) << FrameStats(
        label=Frame("foo", "foo_module.py", 10),
        own=Metric(MetricType.TIME, 0),
        total=Metric(MetricType.TIME, 15),
        height=0,
        children={
            Frame("foobar", "foo_module.py", 5): FrameStats(
                label=Frame("foobar", "foo_module.py", 5),
                own=Metric(MetricType.TIME, 15),
                total=Metric(MetricType.TIME, 15),
                height=1,
            )
        },
    )

    assert frame_stats == FrameStats(
        label=Frame("foo", "foo_module.py", 10),
        own=Metric(MetricType.TIME, 10),
        total=Metric(MetricType.TIME, 35),
        height=0,
        children={
            Frame("foobar", "foo_module.py", 5): FrameStats(
                label=Frame("foobar", "foo_module.py", 5),
                own=Metric(MetricType.TIME, 25),
                total=Metric(MetricType.TIME, 25),
                height=1,
            )
        },
    )


def test_frame_stats_add_partial_matching():
    frame_stats = FrameStats(
        label=Frame("foo", "foo_module.py", 10),
        own=Metric(MetricType.TIME, 10),
        total=Metric(MetricType.TIME, 20),
        height=0,
        children={
            Frame("foobar", "foo_module.py", 5): FrameStats(
                label=Frame("foobar", "foo_module.py", 5),
                own=Metric(MetricType.TIME, 10),
                total=Metric(MetricType.TIME, 10),
                height=1,
            )
        },
    ) << FrameStats(
        label=Frame("foo", "foo_module.py", 10),
        own=Metric(MetricType.TIME, 0),
        total=Metric(MetricType.TIME, 15),
        height=0,
        children={
            Frame("foobar", "bar_module.py", 5): FrameStats(
                label=Frame("foobar", "bar_module.py", 5),
                own=Metric(MetricType.TIME, 15),
                total=Metric(MetricType.TIME, 15),
                height=1,
            )
        },
    )

    assert frame_stats == FrameStats(
        label=Frame("foo", "foo_module.py", 10),
        own=Metric(MetricType.TIME, 10),
        total=Metric(MetricType.TIME, 35),
        height=0,
        children={
            Frame("foobar", "foo_module.py", 5): FrameStats(
                label=Frame("foobar", "foo_module.py", 5),
                own=Metric(MetricType.TIME, 10),
                total=Metric(MetricType.TIME, 10),
                height=1,
            ),
            Frame("foobar", "bar_module.py", 5): FrameStats(
                label=Frame("foobar", "bar_module.py", 5),
                own=Metric(MetricType.TIME, 15),
                total=Metric(MetricType.TIME, 15),
                height=1,
            ),
        },
    )
