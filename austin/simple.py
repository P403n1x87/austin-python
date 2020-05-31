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

import subprocess
import sys
from typing import List

from austin import AustinError, BaseAustin
from austin.cli import AustinArgumentParser


class SimpleAustin(BaseAustin):
    """Simple implementation of Austin.

    This is the simplest way to start Austin from Python if you do not need to
    carry out other operation in parallel. Calling :func:`start` returns only
    once Austin has terminated.

    Example::

        class EchoSimpleAustin(SimpleAustin):
            def on_ready(self, process, child_process, command_line):
                print(f"Austin PID: {process.pid}")
                print(f"Python PID: {child_process.pid}")
                print(f"Command Line: {command_line}")

            def on_sample_received(self, line):
                print(line)

            def on_terminate(self, data):
                print(data)

        try:
            austin = EchoSimpleAustin()
            austin.start(["-i", "10000"], ["python3", "myscript.py"])
        except KeyboardInterrupt:
            pass
    """

    def start(self, args: List[str] = None) -> None:
        """Start the Austin process."""
        try:
            self.proc = subprocess.Popen(
                [self.BINARY] + (args or sys.argv[1:]),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            raise AustinError("Austin executable not found.")

        if not self.proc.stdout:
            raise AustinError("Standard output stream is unexpectedly missing")
        try:
            line = self.proc.stdout.readline()
            if line:
                self._ready_callback(
                    *self._get_process_info(
                        AustinArgumentParser().parse_args(args), self.proc.pid
                    )
                )

            self._running = True

            while line:
                self._sample_callback(line.decode("ascii").rstrip())
                line = self.proc.stdout.readline()

        finally:
            self.proc.wait()
            self._running = False

            if not self.proc.stderr:
                raise AustinError("Standard error stream is unexpectedly missing")

            stderr = (self.proc.stderr.read()).decode().rstrip()
            self._terminate_callback(stderr)
            if self.proc.returncode:
                raise AustinError(f"({self.proc.returncode}) {stderr}")
