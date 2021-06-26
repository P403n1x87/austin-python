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

from pytest import raises

from austin.stats import Frame
from austin.stats import InvalidSample
from austin.stats import Metric
from austin.stats import MetricType
from austin.stats import Sample


def test_sample_alt_format():
    assert Sample.parse(
        "P1;T7fdf1b437700;/usr/lib/python3.6/threading.py:_bootstrap;L884;"
        "/usr/lib/python3.6/threading.py:_bootstrap_inner;L916;"
        "/usr/lib/python3.6/threading.py:run;L864;"
        "test/target34.py:keep_cpu_busy;L31 "
        "10085",
        MetricType.TIME,
    )[0] == Sample(
        1,
        "7fdf1b437700",
        Metric(MetricType.TIME, 10085),
        [
            Frame.parse("/usr/lib/python3.6/threading.py:_bootstrap:884"),
            Frame.parse("/usr/lib/python3.6/threading.py:_bootstrap_inner:916"),
            Frame.parse("/usr/lib/python3.6/threading.py:run:864"),
            Frame.parse("test/target34.py:keep_cpu_busy:31"),
        ],
    )


def test_sample_parser_valid():
    assert Sample.parse(
        "P123;T0x7f546684;foo_module.py:foo:10;bar_module.py:bar:20 42", MetricType.TIME
    )[0] == Sample(
        123,
        "0x7f546684",
        Metric(MetricType.TIME, 42),
        [Frame("foo", "foo_module.py", 10), Frame("bar", "bar_module.py", 20)],
    )

    assert Sample.parse(
        "P1;T0x7f546684;foo_module.py:foo:10;bar_module.py:bar:20 42", MetricType.TIME
    )[0] == Sample(
        1,
        "0x7f546684",
        Metric(MetricType.TIME, 42),
        [Frame("foo", "foo_module.py", 10), Frame("bar", "bar_module.py", 20)],
    )

    assert Sample.parse(
        "P123;T0x7f546684;foo_module.py:foo:10;bar_module.py:bar:20 42,1,-44",
    ) == [
        Sample(
            123,
            "0x7f546684",
            Metric(MetricType.TIME, 0),
            [Frame("foo", "foo_module.py", 10), Frame("bar", "bar_module.py", 20)],
        ),
        Sample(
            123,
            "0x7f546684",
            Metric(MetricType.TIME, 42),
            [Frame("foo", "foo_module.py", 10), Frame("bar", "bar_module.py", 20)],
        ),
        Sample(
            123,
            "0x7f546684",
            Metric(MetricType.MEMORY, 0),
            [Frame("foo", "foo_module.py", 10), Frame("bar", "bar_module.py", 20)],
        ),
        Sample(
            123,
            "0x7f546684",
            Metric(MetricType.MEMORY, 44),
            [Frame("foo", "foo_module.py", 10), Frame("bar", "bar_module.py", 20)],
        ),
    ]

    assert Sample.parse("P1;T0x7f546684 42,0,44") == [
        Sample(
            1,
            "0x7f546684",
            Metric(MetricType.TIME, 42),
            [],
        ),
        Sample(
            1,
            "0x7f546684",
            Metric(MetricType.TIME, 42),
            [],
        ),
        Sample(
            1,
            "0x7f546684",
            Metric(MetricType.MEMORY, 44),
            [],
        ),
        Sample(
            1,
            "0x7f546684",
            Metric(MetricType.MEMORY, 0),
            [],
        ),
    ]


def test_sample_parser_invalid():
    with raises(InvalidSample):  # Empty
        Sample.parse("")

    with raises(InvalidSample):  # Missing Thread
        Sample.parse("foo_module.py:foo:10;bar_module.py:bar:20 42,43,-44")

    with raises(InvalidSample):  # With PID but missing Thread
        Sample.parse("P123;foo_module.py:foo:10;bar_module.py:bar:20 42,43,-44")

    with raises(InvalidSample):  # Completely bonkers
        Sample.parse("snafu")

    with raises(InvalidSample):  # no metrics
        Sample.parse("P1;T0x7f546684;foo_module.py:foo:10;bar_module.py:bar:20")

    with raises(InvalidSample):  # invalid frame
        Sample.parse("P1;T0x7f546684;foo_module.py:foo:10;snafu 10", MetricType.TIME)

    with raises(InvalidSample):  # Invalid number of metrics
        Sample.parse("P1;T0x7f546684;foo_module.py:foo:10 10,20")

    with raises(InvalidSample):  # Too many metrics
        Sample.parse("P1;T0x7f546684;foo_module.py:foo:10 10,20,30,40")


def test_capital_ell():
    assert Sample.parse(
        "P1;T0x7f546684;foo_module.py:foo:10;loo_module.py:Loo:20 10",
        MetricType.TIME,
    )[0] == Sample(
        1,
        "0x7f546684",
        Metric(MetricType.TIME, 10),
        [Frame("foo", "foo_module.py", 10), Frame("Loo", "loo_module.py", 20)],
    )
