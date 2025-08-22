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

from austin.events import AustinFrame
from austin.stats import FrameStats


def test_frame_stats_add_disjoint():
    ref_frame_stats = FrameStats(
        label=AustinFrame(function="foo", filename="foo_module.py", line=10),
        own=10,
        total=20,
        height=0,
        children={
            AustinFrame(
                function="foobar", filename="foo_module.py", line=5
            ): FrameStats(
                label=AustinFrame(function="foobar", filename="foo_module.py", line=5),
                own=10,
                total=10,
                height=1,
            )
        },
    )

    frame_stats = deepcopy(ref_frame_stats) << FrameStats(
        label=AustinFrame(function="bar", filename="bar_module.py", line=10),
        own=10,
        total=20,
        height=0,
        children={
            AustinFrame(
                function="foobar", filename="bar_module.py", line=5
            ): FrameStats(
                label=AustinFrame(function="foobar", filename="bar_module.py", line=5),
                own=10,
                total=10,
                height=1,
            )
        },
    )

    assert frame_stats == ref_frame_stats


def test_frame_stats_add_matching():
    frame_stats = FrameStats(
        label=AustinFrame(function="foo", filename="foo_module.py", line=10),
        own=10,
        total=20,
        height=0,
        children={
            AustinFrame(
                function="foobar", filename="foo_module.py", line=5
            ): FrameStats(
                label=AustinFrame(function="foobar", filename="foo_module.py", line=5),
                own=10,
                total=10,
                height=1,
            )
        },
    ) << FrameStats(
        label=AustinFrame(function="foo", filename="foo_module.py", line=10),
        own=0,
        total=15,
        height=0,
        children={
            AustinFrame(
                function="foobar", filename="foo_module.py", line=5
            ): FrameStats(
                label=AustinFrame(function="foobar", filename="foo_module.py", line=5),
                own=15,
                total=15,
                height=1,
            )
        },
    )

    assert frame_stats == FrameStats(
        label=AustinFrame(function="foo", filename="foo_module.py", line=10),
        own=10,
        total=35,
        height=0,
        children={
            AustinFrame(
                function="foobar", filename="foo_module.py", line=5
            ): FrameStats(
                label=AustinFrame(function="foobar", filename="foo_module.py", line=5),
                own=25,
                total=25,
                height=1,
            )
        },
    )


def test_frame_stats_add_partial_matching():
    frame_stats = FrameStats(
        label=AustinFrame(function="foo", filename="foo_module.py", line=10),
        own=10,
        total=20,
        height=0,
        children={
            AustinFrame(
                function="foobar", filename="foo_module.py", line=5
            ): FrameStats(
                label=AustinFrame(function="foobar", filename="foo_module.py", line=5),
                own=10,
                total=10,
                height=1,
            )
        },
    ) << FrameStats(
        label=AustinFrame(function="foo", filename="foo_module.py", line=10),
        own=0,
        total=15,
        height=0,
        children={
            AustinFrame(
                function="foobar", filename="bar_module.py", line=5
            ): FrameStats(
                label=AustinFrame(function="foobar", filename="bar_module.py", line=5),
                own=15,
                total=15,
                height=1,
            )
        },
    )

    assert frame_stats == FrameStats(
        label=AustinFrame(function="foo", filename="foo_module.py", line=10),
        own=10,
        total=35,
        height=0,
        children={
            AustinFrame(
                function="foobar", filename="foo_module.py", line=5
            ): FrameStats(
                label=AustinFrame(function="foobar", filename="foo_module.py", line=5),
                own=10,
                total=10,
                height=1,
            ),
            AustinFrame(
                function="foobar", filename="bar_module.py", line=5
            ): FrameStats(
                label=AustinFrame(function="foobar", filename="bar_module.py", line=5),
                own=15,
                total=15,
                height=1,
            ),
        },
    )
