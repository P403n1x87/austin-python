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

from abc import ABC, abstractmethod

import psutil


class AustinError(Exception):
    pass


class BaseAustin(ABC):
    def __init__(self, sample_callback=None):
        self._loop = None
        self._pid = -1
        self._cmd_line = "<unknown>"
        self._running = False

        try:
            self._callback = (
                sample_callback if sample_callback else self.on_sample_received
            )
        except AttributeError as e:
            raise RuntimeError("No sample callback given or implemented.") from e

    def post_process_start(self):
        if not self._pid or self._pid < 0:  # Austin is forking
            austin_process = psutil.Process(self.proc.pid)
            while not austin_process.children():
                pass
            child_process = austin_process.children()[0]
            if child_process.pid is not None:
                self._pid = child_process.pid
        else:  # Austin is attaching
            try:
                child_process = psutil.Process(self._pid)
            except psutil.NoSuchProcess:
                raise AustinError(
                    f"Cannot attach to process with PID {self._pid} because it does not seem to exist."
                )

        self._child = child_process
        self._cmd_line = " ".join(child_process.cmdline())

    @abstractmethod
    def start(self, args):
        ...

    def get_pid(self):
        return self._pid

    def get_cmd_line(self):
        return self._cmd_line

    def is_running(self):
        return self._running

    def get_child(self):
        return self._child

    @abstractmethod
    def wait(self, timeout=1):
        ...


# ---- TEST ----

if __name__ == "__main__":

    class MyAsyncAustin(AsyncAustin):
        def on_sample_received(self, line):
            print(line)

    try:
        austin = MyAsyncAustin()
        austin.start(["-i", "10000", "python3", "test/target34.py"])
        austin.join()
    except KeyboardInterrupt:
        print("Bye!")

    class MyThreadedAustin(ThreadedAustin):
        def on_sample_received(self, line):
            print(line)

    try:
        austin = MyThreadedAustin()
        austin.start(["-i", "10000", "python3", "test/target34.py"])
        austin.join()
    except KeyboardInterrupt:
        print("Bye!")
