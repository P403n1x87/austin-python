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

import asyncio
import sys

from pytest import raises

from austin import AustinError
from austin.aio import AsyncAustin


if sys.platform == "win32":
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)


class TestAsyncAustin(AsyncAustin):
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
        assert self._ready
        assert self._sample_received
        assert self._terminate


class InvalidBinaryAsyncAustin(AsyncAustin):
    BINARY = "_austin"


def test_async_time():
    austin = TestAsyncAustin()

    asyncio.get_event_loop().run_until_complete(
        austin.start(
            [
                "-t",
                "10",
                "-Ci",
                "100",
                "python",
                "-c",
                "from time import sleep; sleep(2)",
            ]
        )
    )

    austin.assert_callbacks_called()

    assert austin.version is not None
    assert austin.python_version is not None


def test_async_memory():
    austin = TestAsyncAustin()

    def sample_callback(data):
        austin._sample_received = True

    austin._sample_callback = sample_callback
    asyncio.get_event_loop().run_until_complete(
        austin.start(
            [
                "-t",
                "10",
                "-mCi",
                "100",
                "python",
                "-c",
                "[i for i in range(10000000)]",
            ]
        )
    )
    austin.assert_callbacks_called()


def test_async_terminate():
    austin = TestAsyncAustin()

    def sample_callback(*args):
        austin._sample_received = True
        austin.terminate()

    def terminate_callback(*args):
        austin._terminate = True

    austin._sample_callback = sample_callback
    austin._terminate_callback = terminate_callback

    try:
        asyncio.get_event_loop().run_until_complete(
            asyncio.wait_for(austin.start(["-t", "10", "-Ci", "10ms", "python"]), 30)
        )
    except AustinError:
        austin.assert_callbacks_called()


def test_async_invalid_binary():
    with raises(AustinError):
        asyncio.get_event_loop().run_until_complete(
            InvalidBinaryAsyncAustin(sample_callback=lambda x: None).start(["python"])
        )


def test_async_no_sample_callback():
    with raises(AustinError):
        InvalidBinaryAsyncAustin()


def test_async_bad_options():
    austin = TestAsyncAustin(terminate_callback=lambda *args: None)
    with raises(AustinError):
        asyncio.get_event_loop().run_until_complete(
            austin.start(
                ["-I", "1000", "python", "-c", "for i in range(1000000): print(i)"]
            )
        )
