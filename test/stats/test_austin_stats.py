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

from austin.stats import (AustinStats, Frame, FrameStats, Metrics,
                          ProcessStats, Sample, ThreadStats)


def test_austin_stats_single_process():
    stats = AustinStats(42)

    stats.update(Sample.parse("Thread 0x7f45645646;foo (foo_module.py:10) 152"))
    assert stats == AustinStats(
        child_pid=42,
        processes={
            42: ProcessStats(
                pid=42,
                threads={
                    "Thread 0x7f45645646": ThreadStats(
                        label="Thread 0x7f45645646",
                        total=Metrics(152),
                        children={
                            Frame("foo", "foo_module.py", 10): FrameStats(
                                label=Frame("foo", "foo_module.py", 10),
                                own=Metrics(152),
                                total=Metrics(152),
                            )
                        },
                    )
                },
            )
        },
    )

    stats.update(Sample.parse("Thread 0x7f45645646 148"))
    assert stats == AustinStats(
        child_pid=42,
        processes={
            42: ProcessStats(
                pid=42,
                threads={
                    "Thread 0x7f45645646": ThreadStats(
                        label="Thread 0x7f45645646",
                        total=Metrics(300),
                        own=Metrics(148),
                        children={
                            Frame("foo", "foo_module.py", 10): FrameStats(
                                label=Frame("foo", "foo_module.py", 10),
                                own=Metrics(152),
                                total=Metrics(152),
                            )
                        },
                    )
                },
            )
        },
    )

    stats.update(Sample.parse("Thread 0x7f45645646;foo (foo_module.py:10) 100"))
    assert stats == AustinStats(
        child_pid=42,
        processes={
            42: ProcessStats(
                pid=42,
                threads={
                    "Thread 0x7f45645646": ThreadStats(
                        label="Thread 0x7f45645646",
                        total=Metrics(400),
                        own=Metrics(148),
                        children={
                            Frame("foo", "foo_module.py", 10): FrameStats(
                                label=Frame("foo", "foo_module.py", 10),
                                own=Metrics(252),
                                total=Metrics(252),
                            )
                        },
                    )
                },
            )
        },
    )

    stats.update(Sample.parse("Thread 0x7f45645646;bar (foo_module.py:35) 400"))
    assert stats == AustinStats(
        child_pid=42,
        processes={
            42: ProcessStats(
                pid=42,
                threads={
                    "Thread 0x7f45645646": ThreadStats(
                        label="Thread 0x7f45645646",
                        total=Metrics(800),
                        own=Metrics(148),
                        children={
                            Frame("foo", "foo_module.py", 10): FrameStats(
                                label=Frame("foo", "foo_module.py", 10),
                                own=Metrics(252),
                                total=Metrics(252),
                            ),
                            Frame("bar", "foo_module.py", 35): FrameStats(
                                label=Frame("bar", "foo_module.py", 35),
                                own=Metrics(400),
                                total=Metrics(400),
                            ),
                        },
                    )
                },
            )
        },
    )

    stats.update(Sample.parse("Thread 0x7f45645664;foo (foo_module.py:10) 152"))
    assert stats == AustinStats(
        child_pid=42,
        processes={
            42: ProcessStats(
                pid=42,
                threads={
                    "Thread 0x7f45645664": ThreadStats(
                        label="Thread 0x7f45645664",
                        total=Metrics(152),
                        children={
                            Frame("foo", "foo_module.py", 10): FrameStats(
                                label=Frame("foo", "foo_module.py", 10),
                                own=Metrics(152),
                                total=Metrics(152),
                            )
                        },
                    ),
                    "Thread 0x7f45645646": ThreadStats(
                        label="Thread 0x7f45645646",
                        total=Metrics(800),
                        own=Metrics(148),
                        children={
                            Frame("foo", "foo_module.py", 10): FrameStats(
                                label=Frame("foo", "foo_module.py", 10),
                                own=Metrics(252),
                                total=Metrics(252),
                            ),
                            Frame("bar", "foo_module.py", 35): FrameStats(
                                label=Frame("bar", "foo_module.py", 35),
                                own=Metrics(400),
                                total=Metrics(400),
                            ),
                        },
                    ),
                },
            )
        },
    )
