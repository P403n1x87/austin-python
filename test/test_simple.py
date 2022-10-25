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

import os
import os.path
import tempfile
from pathlib import Path

import toml
from pytest import raises

from austin import AustinError
from austin.config import AustinConfiguration as AC
from austin.simple import SimpleAustin


class TestSimpleAustin(SimpleAustin):
    __test__ = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ready = False
        self._sample_received = False
        self._terminate = False

    def on_ready(self, process, child_process, command_line):
        assert process.pid != child_process.pid
        assert "python" in self.get_command_line().lower()
        self._ready = True

    def on_sample_received(self, line):
        assert line
        self._sample_received = True

    def on_terminate(self, data):
        assert "duration" in data
        assert "errors" in data
        assert "sampling" in data
        assert "saturation" in data
        self._terminate = True

    def assert_callbacks_called(self):
        assert self._ready and self._sample_received and self._terminate


class InvalidBinarySimpleAustin(SimpleAustin):
    BINARY = "_austin"


def test_simple():
    austin = TestSimpleAustin()

    austin.start(["-Ci", "1000", "python", "-c", "from time import sleep; sleep(1)"])

    austin.assert_callbacks_called()

    assert austin.version is not None
    assert austin.python_version is not None


def test_simple_invalid_binary():
    with raises(AustinError):
        InvalidBinarySimpleAustin(sample_callback=lambda x: None).start(["python"])


def test_simple_no_sample_callback():
    with raises(AustinError):
        InvalidBinarySimpleAustin()


def test_simple_bad_options():
    austin = TestSimpleAustin(terminate_callback=lambda *args: None)
    with raises(AustinError):
        austin.start(
            ["-I", "1000", "python", "-c", "for i in range(1000000): print(i)"]
        )


def assert_binary_path(path: Path):
    assert Path(TestSimpleAustin().binary_path).resolve() == path.resolve()


def test_binary_path_cwd():
    with tempfile.TemporaryDirectory() as tempdir:
        old_cwd = Path.cwd()
        os.chdir(tempdir)

        Path(TestSimpleAustin.BINARY).write_text("Hello")

        assert_binary_path(Path.cwd() / TestSimpleAustin.BINARY)

        os.chdir(old_cwd)


def test_binary_path_austinpath():
    with tempfile.TemporaryDirectory() as tempdir:
        old_path = os.environ.get("AUSTINPATH")

        os.environ["AUSTINPATH"] = tempdir
        temp_binary = Path(tempdir) / TestSimpleAustin.BINARY
        temp_binary.write_text("Hello")

        assert_binary_path(temp_binary)

        if old_path is not None:
            os.environ["AUSTINPATH"] = old_path


def test_binary_path_rc():
    with tempfile.TemporaryDirectory() as tempdir:
        old_home = os.environ.get("HOME")
        old_path = os.environ.get("AUSTINPATH")
        del os.environ["AUSTINPATH"]

        home = os.environ["HOME"] = tempdir
        AC.RC = os.path.join(home, ".austinrc")
        with open(AC.RC, "w") as fout:
            toml.dump({"binary": AC.RC}, fout)

        AC().reload()

        assert_binary_path(Path(AC.RC))

        if old_path is not None:
            os.environ["AUSTINPATH"] = old_path
        if old_home is not None:
            os.environ["HOME"] = old_home
