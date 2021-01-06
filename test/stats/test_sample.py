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

from austin.stats import Frame, InvalidSample, Metrics, Sample
from pytest import raises


def test_sample_alt_format():
    assert Sample.parse(
        "P1;T7fdf1b437700;_bootstrap (/usr/lib/python3.6/threading.py);L884;"
        "_bootstrap_inner (/usr/lib/python3.6/threading.py);L916;"
        "run (/usr/lib/python3.6/threading.py);L864;"
        "keep_cpu_busy (test/target34.py);L31 "
        "10085"
    ) == Sample(
        1,
        "7fdf1b437700",
        Metrics(10085),
        [
            Frame.parse("_bootstrap (/usr/lib/python3.6/threading.py:884)"),
            Frame.parse("_bootstrap_inner (/usr/lib/python3.6/threading.py:916)"),
            Frame.parse("run (/usr/lib/python3.6/threading.py:864)"),
            Frame.parse("keep_cpu_busy (test/target34.py:31)"),
        ],
    )


def test_sample_parser_valid():
    assert Sample.parse(
        "P123;T0x7f546684;foo (foo_module.py:10);bar (bar_module.py:20) 42"
    ) == Sample(
        123,
        "0x7f546684",
        Metrics(42),
        [Frame("foo", "foo_module.py", 10), Frame("bar", "bar_module.py", 20)],
    )

    assert Sample.parse(
        "P1;T0x7f546684;foo (foo_module.py:10);bar (bar_module.py:20) 42"
    ) == Sample(
        1,
        "0x7f546684",
        Metrics(42),
        [Frame("foo", "foo_module.py", 10), Frame("bar", "bar_module.py", 20)],
    )

    assert Sample.parse(
        "P123;T0x7f546684;foo (foo_module.py:10);bar (bar_module.py:20) " "42 43 -44"
    ) == Sample(
        123,
        "0x7f546684",
        Metrics(42, 43, -44),
        [Frame("foo", "foo_module.py", 10), Frame("bar", "bar_module.py", 20)],
    )

    assert Sample.parse(
        "P1;T0x7f546684;foo (foo_module.py:10);bar (bar_module.py:20) 42 43 -44"
    ) == Sample(
        1,
        "0x7f546684",
        Metrics(42, 43, -44),
        [Frame("foo", "foo_module.py", 10), Frame("bar", "bar_module.py", 20)],
    )

    assert Sample.parse("P1;T0x7f546684 42 43 -44") == Sample(
        1, "0x7f546684", Metrics(42, 43, -44), []
    )


def test_sample_parser_invalid():
    with raises(InvalidSample):  # Empty
        Sample.parse("")

    with raises(InvalidSample):  # Missing Thread
        Sample.parse("foo (foo_module.py:10);bar (bar_module.py:20) 42 43 -44")

    with raises(InvalidSample):  # With PID but missing Thread
        Sample.parse("P123;foo (foo_module.py:10);bar (bar_module.py:20) 42 43 -44")

    with raises(InvalidSample):  # Completely bonkers
        Sample.parse("snafu")

    with raises(InvalidSample):  # no metrics
        Sample.parse("P1;T0x7f546684;foo (foo_module.py:10);bar (bar_module.py:20)")

    with raises(InvalidSample):  # invalid frame
        Sample.parse("P1;T0x7f546684;foo (foo_module.py:10);snafu 10")

    with raises(InvalidSample):  # Invalid number of metrics
        Sample.parse("P1;T0x7f546684;foo (foo_module.py:10) 10 20")

    with raises(InvalidSample):  # Too many metrics
        Sample.parse("P1;T0x7f546684;foo (foo_module.py:10) 10 20 30 40")


def test_capital_ell():
    assert Sample.parse(
        "P1;T0x7f546684;foo (foo_module.py:10);Loo (loo_module.py:20) 10"
    ) == Sample(
        1,
        "0x7f546684",
        Metrics(10),
        [Frame("foo", "foo_module.py", 10), Frame("Loo", "loo_module.py", 20)],
    )
