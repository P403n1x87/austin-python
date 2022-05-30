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

from austin.cli import AustinArgumentParser
from austin.cli import AustinCommandLineError


class Bunch:
    def __getattr__(self, name):
        return self.__dict__.get(name)


def test_missing_command_and_pid():
    with raises(AustinCommandLineError):
        AustinArgumentParser().parse_args([])

    with raises(AustinCommandLineError):
        AustinArgumentParser(pid=False, command=False)


def test_command_with_options():
    args = AustinArgumentParser().parse_args(
        ["-i", "1000", "python3", "-c", 'print("Test")']
    )

    assert args.command == ["python3", "-c", 'print("Test")']


def test_command_with_options_and_arguments():
    args = AustinArgumentParser().parse_args(
        ["-i", "1000", "python3", "my_app.py", "-c", 'print("Test")']
    )

    assert args.command == ["python3", "my_app.py", "-c", 'print("Test")']


def test_command_with_austin_args():
    args = AustinArgumentParser().parse_args(
        ["-i", "1000", "python3", "my_app.py", "-i", "100"]
    )

    assert args.interval == 1000
    assert args.command == ["python3", "my_app.py", "-i", "100"]


def test_exposure():
    assert 2 == AustinArgumentParser().parse_args(["-x", "2", "python3"]).exposure


def test_time_units():
    assert 1000 == AustinArgumentParser().parse_args(["-i", "1ms", "python3"]).interval
    assert 1000 == AustinArgumentParser().parse_args(["-t", "1s", "python3"]).timeout
    assert 2 == AustinArgumentParser().parse_args(["-x", "2s", "python3"]).exposure
    with raises(AustinCommandLineError):
        AustinArgumentParser().parse_args(["-x", "2ls", "python3"]).exposure
    with raises(AustinCommandLineError):
        AustinArgumentParser().parse_args(["-x", "2l", "python3"]).exposure


def test_pid_only():
    args = AustinArgumentParser().parse_args(["-i", "1000", "-p", "1086"])

    assert args.pid == 1086


def test_args_list():

    args = Bunch()
    args.alt_format = True
    args.children = True
    args.exclude_empty = True
    args.full = True
    args.interval = 1000
    args.memory = True
    args.pid = 42
    args.sleepless = True
    args.timeout = 50
    args.command = ["python3", "somescript.py"]

    args.foo = "bar"

    assert AustinArgumentParser.to_list(args) == [
        "-a",
        "-C",
        "-e",
        "-f",
        "-i",
        "1000",
        "-m",
        "-p",
        "42",
        "-s",
        "-t",
        "50",
        "python3",
        "somescript.py",
    ]

    assert AustinArgumentParser.to_list(
        AustinArgumentParser().parse_args(["-i", "1ms", "python"])
    ) == [
        "-i",
        "1000",
        "python",
    ]
