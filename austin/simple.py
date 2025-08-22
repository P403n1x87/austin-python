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
import typing as t

from austin.base import AustinState
from austin.base import BaseAustin
from austin.cli import AustinArgumentParser
from austin.errors import AustinError
from austin.events import AustinMetadata
from austin.events import AustinSample
from austin.format.mojo import MojoStreamReader


class SimpleAustin(BaseAustin):
    """Simple implementation of Austin.

    This is the simplest way to start Austin from Python if you do not need to
    carry out other operation in parallel. The following example shows how to
    make a simple implementation of Austin that returns stack in the collapsed
    format

    Example::

        from austin.events import AustinMetadata, AustinSample
        from austin.format.collapsed_stack import AustinEventCollapsedStackFormatter
        from austin.simple import SimpleAustin

        FORMATTER = AustinEventCollapsedStackFormatter()


        class CollapsedStackSimpleAustin(SimpleAustin):
            def on_metadata(self, metadata: AustinMetadata) -> None:
                print(FORMATTER.format(metadata))

            def on_sample(self, sample: AustinSample) -> None:
                print(FORMATTER.format(sample))


        austin = CollapsedStackSimpleAustin()
        austin.start(["-i", "10ms", "python3", "myscript.py"])
        austin.wait()
    """

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)

        self._proc: t.Optional[subprocess.Popen] = None
        self._mojo: t.Optional[MojoStreamReader] = None

    def start(self, args: t.Optional[t.Sequence[str]] = None) -> None:
        """Start the Austin process."""
        self._args = AustinArgumentParser().parse_args(args)

        self._state = AustinState.STARTING

        try:
            self._proc = subprocess.Popen(
                [
                    str(self.binary_path),
                    "-P",
                    *(args if args is not None else sys.argv[1:]),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            raise AustinError("Austin executable not found.") from None

        if not self._proc.stdout:
            raise AustinError("Standard output stream is unexpectedly missing")
        if not self._proc.stderr:
            raise AustinError("Standard error stream is unexpectedly missing")

        self._mojo = MojoStreamReader(self._proc.stdout)

        # Retrieve the Austin version, then call the ready callback
        for e in self._mojo:
            if isinstance(e, AustinMetadata):
                self._meta[e.name] = e.value

                try:
                    if self._metadata_callback is not None:
                        self._metadata_callback(e)
                except Exception as exc:
                    raise AustinError("Error in call to metadata callback") from exc

                if e.name == "austin":
                    self._check_version()
                    break
        else:
            raise AustinError("Cannot determine Austin version from output")

    def terminate(self) -> None:
        """Terminate the Austin process."""
        if self._proc is None:
            raise AustinError("Austin process is not running")

        self._proc.terminate()

    def wait(self) -> int:
        if self._proc is None:
            raise AustinError("Austin process is not running")

        self._state = AustinState.RUNNING

        assert self._mojo is not None

        for e in self._mojo:
            if isinstance(e, AustinSample):
                try:
                    self._sample_callback(e)
                except Exception as exc:
                    raise AustinError("Error in call to sample callback") from exc
            elif isinstance(e, AustinMetadata):
                self._meta[e.name] = e.value
                if self._metadata_callback is not None:
                    try:
                        self._metadata_callback(e)
                    except Exception as exc:
                        raise AustinError("Error in call to metadata callback") from exc

        self._state = AustinState.TERMINATING

        # Call the terminate callback
        try:
            if self._terminate_callback is not None:
                self._terminate_callback()
        except Exception as exc:
            raise AustinError("Error in call to terminate callback") from exc

        try:
            return self._proc.wait()
        finally:
            self._state = AustinState.TERMINATED
