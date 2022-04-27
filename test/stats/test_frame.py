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
from austin.stats import InvalidFrame


def test_frame_parser_valid():
    assert Frame.parse("/tmp/bar.py:foo:10") == Frame("foo", "/tmp/bar.py", 10)
    assert Frame.parse("<module>:foo:42") == Frame("foo", "<module>", 42)


def test_frame_parser_invalid():
    with raises(InvalidFrame):  # Completely bonkers
        Frame.parse("snafu")

    with raises(InvalidFrame):  # Empty
        Frame.parse("")

    with raises(InvalidFrame):
        Frame.parse("foo (<module>:bar)")  # Invalid line number


def test_frame_str():
    assert str(Frame("foo", "foo_module", 10)) == "foo_module:foo:10"


def test_frame_win_drive():
    assert Frame.parse("C:\\user\\bar.py:foo:42") == Frame(
        "foo", "C:\\user\\bar.py", 42
    )
