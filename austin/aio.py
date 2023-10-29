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
from typing import Dict
from typing import List
from typing import Optional

from austin import AustinError
from austin import BaseAustin
from austin.cli import AustinArgumentParser


class AsyncAustin(BaseAustin):
    """Asynchronous implementation of Austin.

    Implements an ``asyncio`` API for Austin so that it can be used alongside
    other asynchronous tasks.

    The following example shows how to make a simple asynchronous echo
    implementation of Austin that behaves exactly just like Austin.

    Example::

        class EchoAsyncAustin(AsyncAustin):
            def on_ready(self, process, child_process, command_line):
                print(f"Austin PID: {process.pid}")
                print(f"Python PID: {child_process.pid}")
                print(f"Command Line: {command_line}")

            def on_sample_received(self, line):
                print(line)

            def on_terminate(self, data):
                print(data)

        if sys.platform == "win32":
            asyncio.set_event_loop(asyncio.ProactorEventLoop())

        try:
            austin = EchoAsyncAustin()
            asyncio.get_event_loop().run_until_complete(
                austin.start(["-i", "10000", "python3", "myscript.py"])
            )
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
    """

    async def _read_stderr(self) -> Optional[str]:
        assert self.proc.stderr is not None

        try:
            return (
                (await asyncio.wait_for(self.proc.stderr.read(), 0.1)).decode().rstrip()
            )
        except asyncio.TimeoutError:
            return None

    async def _read_meta(self) -> Dict[str, str]:
        assert self.proc.stdout is not None

        meta = {}

        while True:
            line = (await self.proc.stdout.readline()).decode().rstrip()
            if not (line and line.startswith("# ")):
                break
            key, _, value = line[2:].partition(": ")
            meta[key] = value

        self._meta.update(meta)
        return meta

    async def start(self, args: Optional[List[str]] = None) -> None:
        """Create the start coroutine.

        Use with the ``asyncio`` event loop.
        """
        try:
            _args = list(args if args is not None else sys.argv[1:])  # Make a copy
            _args.insert(0, "-P")
            self.proc = await asyncio.create_subprocess_exec(
                self.binary_path,
                *_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            raise AustinError("Austin executable not found.") from None

        if not self.proc.stdout:
            raise AustinError("Standard output stream is unexpectedly missing")
        if not self.proc.stderr:
            raise AustinError("Standard error stream is unexpectedly missing")

        self._running = True

        try:
            if not await self._read_meta():
                raise AustinError("Austin did not start properly")

            self.check_version()

            self._ready_callback(
                *self._get_process_info(
                    AustinArgumentParser().parse_args(args), self.proc.pid
                )
            )

            # Start readline loop
            while self._running:
                data = (await self.proc.stdout.readline()).rstrip()
                if not data:
                    break

                self.submit_sample(data)

            self._terminate_callback(await self._read_meta())
            self.check_exit(await self.proc.wait(), await self._read_stderr())

        except Exception:
            try:
                self.proc.terminate()
                await self.proc.wait()
            except Exception:
                # best effort
                pass
            raise

        finally:
            self._running = False
