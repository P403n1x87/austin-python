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

import sys
from pathlib import Path

import pytest

from austin.errors import AustinError
from austin.threads import ThreadedAustin


class TestThreadedAustin(ThreadedAustin):
    __test__ = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._metadata = False
        self._sample_received = False
        self._terminate = False

    def on_metadata(self, metadata):
        assert metadata
        self._metadata = True

    def on_sample(self, sample):
        assert sample
        self._sample_received = True

    def on_terminate(self):
        data = self._meta
        assert "duration" in data
        assert "errors" in data
        assert "sampling" in data
        assert "saturation" in data
        self._terminate = True

    def assert_callbacks_called(self):
        assert self._metadata and self._sample_received and self._terminate


class InvalidBinaryThreadedAustin(ThreadedAustin):
    BINARY = Path("_austin")


def test_threaded():
    austin = TestThreadedAustin()

    austin.start(["-i", "1000", "python", "-c", "from time import sleep; sleep(2)"])
    assert austin.wait() == 0

    austin.assert_callbacks_called()

    assert austin.version is not None
    assert austin.python_version is not None


@pytest.mark.skipif(
    sys.platform == "win32", reason="Signal handling not supported on Windows"
)
def test_threaded_terminate():
    austin = TestThreadedAustin()

    def sample_callback(*args):
        if not austin._sample_received:
            austin.terminate()
        austin._sample_received = True

    def terminate_callback(*args):
        austin._terminate = True

    austin._sample_callback = sample_callback
    austin._terminate_callback = terminate_callback

    austin.start(["-i", "100", "python", "-c", "from time import sleep; sleep(1)"])

    assert austin.wait() != 0

    austin.assert_callbacks_called()


def test_threaded_invalid_binary():
    austin = InvalidBinaryThreadedAustin(sample_callback=lambda x: None)
    austin.start(["python"])
    with pytest.raises(AustinError):
        austin.join()


def test_threaded_no_sample_callback():
    with pytest.raises(AustinError):
        InvalidBinaryThreadedAustin()


def test_threaded_bad_options():
    austin = TestThreadedAustin(terminate_callback=lambda *args: None)
    austin.start(["-I", "1000", "python", "-c", "for i in range(1000000): print(i)"])
    with pytest.raises(AustinError):
        austin.join()
