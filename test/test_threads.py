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

from austin import AustinError
from austin import AustinTerminated
from austin.simple import SimpleAustin
from austin.threads import ThreadedAustin


def check_raises(exc):
    def _check_raises_decorator(f):
        def _check_raises_wrapper(*args, **kwargs):
            with raises(exc):
                f(*args, **kwargs)

        return _check_raises_wrapper

    return _check_raises_decorator


class TestThreadedAustin(ThreadedAustin):
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


class InvalidBinaryThreadedAustin(ThreadedAustin):
    BINARY = "_austin"

    @check_raises(AustinError)
    def run(self, *args, **kwargs):
        super().run(*args, **kwargs)


def test_threaded():
    austin = TestThreadedAustin()

    austin.start(["-i", "1000", "python", "-c", "from time import sleep; sleep(2)"])
    austin.join()

    austin.assert_callbacks_called()

    assert austin.version is not None
    assert austin.python_version is not None


def test_threaded_terminate():
    austin = TestThreadedAustin()

    def sample_callback(*args):
        austin._sample_received = True
        austin.terminate()

    def terminate_callback(*args):
        austin._terminate = True

    austin._sample_callback = sample_callback
    austin._terminate_callback = terminate_callback

    austin.start(["-i", "100", "python", "-c", "from time import sleep; sleep(1)"])
    with raises(AustinTerminated):
        austin.join()
    austin.assert_callbacks_called()


def test_threaded_invalid_binary():
    SimpleAustin.start = check_raises(AustinError)(SimpleAustin.start)
    InvalidBinaryThreadedAustin(sample_callback=lambda x: None).start(["python"])


def test_threaded_no_sample_callback():
    with raises(AustinError):
        InvalidBinaryThreadedAustin()


def test_threaded_bad_options():
    austin = TestThreadedAustin(terminate_callback=lambda *args: None)
    austin.start(["-I", "1000", "python", "-c", "for i in range(1000000): print(i)"])
    austin.join()
