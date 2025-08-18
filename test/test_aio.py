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
from pathlib import Path

import pytest
from pytest import raises

from austin.aio import AsyncAustin
from austin.errors import AustinError
from austin.events import AustinMetadata
from austin.events import AustinSample


if sys.platform == "win32":
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)


class TestAsyncAustin(AsyncAustin):
    __test__ = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._metadata = False
        self._sample_received = False
        self._terminate = False

    async def on_sample(self, sample: AustinSample) -> None:
        assert sample
        self._sample_received = True

    async def on_metadata(self, metadata: AustinMetadata) -> None:
        assert metadata
        self._metadata = True

    async def on_terminate(self):
        data = self._meta
        assert "duration" in data
        assert "errors" in data
        assert "sampling" in data
        assert "saturation" in data
        self._terminate = True

    def assert_callbacks_called(self):
        assert self._metadata
        assert self._sample_received
        assert self._terminate


class InvalidBinaryAsyncAustin(AsyncAustin):
    BINARY = Path("_austin")


@pytest.mark.asyncio
async def test_async_time():
    austin = TestAsyncAustin()

    await austin.start(
        [
            "-Ci",
            "100",
            "python",
            "-c",
            "from time import sleep; sleep(2)",
        ]
    )
    await asyncio.wait_for(austin.wait(), 30)

    austin.assert_callbacks_called()

    assert austin.version is not None
    assert austin.python_version is not None


@pytest.mark.asyncio
async def test_async_memory():
    austin = TestAsyncAustin()

    async def sample_callback(data):
        austin._sample_received = True

    austin._sample_callback = sample_callback
    await austin.start(
        [
            "-mCi",
            "100",
            "python",
            "-c",
            "[i for i in range(10000000)]",
        ]
    )
    await asyncio.wait_for(austin.wait(), 30)

    austin.assert_callbacks_called()


@pytest.mark.skipif(
    sys.platform == "win32", reason="Signal handling not supported on Windows"
)
@pytest.mark.asyncio
async def test_async_terminate():
    austin = TestAsyncAustin()

    async def sample_callback(sample):
        assert sample
        if not austin._sample_received:
            austin.terminate()
        austin._sample_received = True

    async def terminate_callback():
        austin._terminate = True

    austin._sample_callback = sample_callback
    austin._terminate_callback = terminate_callback

    await austin.start(["-Ci", "10ms", "python"])
    await asyncio.wait_for(austin.wait(), 30)

    austin.assert_callbacks_called()


@pytest.mark.asyncio
async def test_async_invalid_binary():
    with raises(AustinError):
        await InvalidBinaryAsyncAustin(sample_callback=lambda x: None).start(["python"])


def test_async_no_sample_callback():
    with raises(AustinError):
        InvalidBinaryAsyncAustin()


@pytest.mark.asyncio
async def test_async_bad_options():
    austin = TestAsyncAustin(terminate_callback=lambda *args: None)
    with raises(AustinError):
        await austin.start(
            ["-I", "1000", "python", "-c", "for i in range(1000000): print(i)"]
        )
