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

import typing as t
from threading import Thread

from austin.errors import AustinError
from austin.simple import SimpleAustin


class ThreadedAustin(SimpleAustin):
    """Thread-based implementation of Austin.

    Implements a ``threading`` API for Austin so that it can be used alongside
    other threads.

    The following example shows how to make a simple threaded echo
    implementation of Austin that behaves exactly just like Austin.

    Example::

        from austin.events import AustinMetadata, AustinSample
        from austin.format.collapsed_stack import AustinEventCollapsedStackFormatter
        from austin.threads import ThreadedAustin

        FORMATTER = AustinEventCollapsedStackFormatter()


        class CollapsedStackThreadedAustin(ThreadedAustin):
            def on_metadata(self, metadata: AustinMetadata) -> None:
                print(FORMATTER.format(metadata))

            def on_sample(self, sample: AustinSample) -> None:
                print(FORMATTER.format(sample))


        austin = CollapsedStackThreadedAustin()
        austin.start(["-i", "10ms", "python3", "myscript.py"])
        austin.wait()
    """

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)

        self._thread: t.Optional[Thread] = None
        self._exc: t.Optional[Exception] = None
        self._exit_code: t.Optional[int] = None

    def start(self, args: t.Optional[t.Sequence[str]] = None) -> None:
        """Start the Austin thread."""

        def _thread_bootstrap(self: ThreadedAustin) -> None:
            try:
                super().start(args)
                self._exit_code = super().wait()

            except Exception as e:
                self._exc = e

        self._thread = Thread(target=_thread_bootstrap, args=(self,))
        self._thread.start()

    def join(self, timeout: t.Optional[float] = None) -> None:
        """Join the thread.

        This is the same as calling :func:`join` on the underlying thread
        object.

        **Note**
            This is an extension of the base Austin abstract class.
        """
        if self._thread is None:
            raise AustinError("Austin thread has not been started yet")
        self._thread.join(timeout)
        if self._exc:
            raise self._exc

    def wait(self) -> int:
        """Wait for the Austin thread to finish and return the exit code."""
        if self._thread is None:
            raise AustinError("Austin thread has not been started yet")

        self.join()

        if self._exc:
            raise self._exc

        assert self._exit_code is not None

        return self._exit_code
