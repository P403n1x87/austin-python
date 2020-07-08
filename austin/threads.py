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

from threading import Thread
from typing import Any, List, Optional

from austin import AustinError
from austin.simple import SimpleAustin


class ThreadedAustin(SimpleAustin):
    """Thread-based implementation of Austin.

    Implements a ``threading`` API for Austin so that it can be used alongside
    other threads.

    The following example shows how to make a simple threaded echo
    implementation of Austin that behaves exactly just like Austin.

    Example::

        class EchoThreadedAustin(ThreadedAustin):
            def on_ready(self, process, child_process, command_line):
                print(f"Austin PID: {process.pid}")
                print(f"Python PID: {child_process.pid}")
                print(f"Command Line: {command_line}")

            def on_sample_received(self, line):
                print(line)

            def on_terminate(self, data):
                print(data)

        try:
            austin = EchoThreadedAustin()
            austin.start(["-i", "10000", "python3", "myscript.py"])
            austin.join()
        except KeyboardInterrupt:
            pass
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self._thread: Optional[Thread] = None
        self._exc: Optional[Exception] = None

    def start(self, args: List[str] = None) -> None:
        """Start the Austin thread."""

        def _thread_bootstrap() -> None:
            try:
                SimpleAustin.start(self, args)
            except Exception as e:
                self._exc = e

        self._thread = Thread(target=_thread_bootstrap)
        self._thread.start()

    def get_thread(self) -> Optional[Thread]:
        """Get the underlying :class:`threading.Thread` instance.

        As this leaks a bit of the implementation, interaction with the
        returned thread object should be done with care.

        **Note**
            This is an extension of the base Austin abstract class.
        """
        return self._thread

    def join(self, timeout: float = None) -> None:
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
