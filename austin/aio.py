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
import typing as t

from austin.base import AustinState
from austin.base import BaseAustin
from austin.cli import AustinArgumentParser
from austin.errors import AustinError
from austin.events import AustinMetadata
from austin.events import AustinSample
from austin.format.mojo import AsyncMojoStreamReader


class AsyncAustin(BaseAustin):
    """Asynchronous implementation of Austin.

    Implements an ``asyncio`` API for Austin so that it can be used alongside
    other asynchronous tasks.

    The following example shows how to make a simple asynchronous implementation
    of Austin that returns stack in the collapsed format

    Example::

        import asyncio
        import sys

        from austin.aio import AsyncAustin
        from austin.format.collapsed_stack import AustinEventCollapsedStackFormatter

        FORMATTER = AustinEventCollapsedStackFormatter()


        class CollapsedStackAsyncAustin(AsyncAustin):
            async def on_sample(self, sample):
                print(FORMATTER.format(sample))

            async def on_metadata(self, metadata):
                print(FORMATTER.format(metadata))


        if sys.platform == "win32":
            asyncio.set_event_loop(asyncio.ProactorEventLoop())


        async def main():
            austin = CollapsedStackAsyncAustin()
            await austin.start(["-i", "10ms", "python", "myscript.py"])
            await austin.wait()


        asyncio.run(main())
    """

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)

        self._run_task: t.Optional[asyncio.Task] = None
        self._proc: t.Optional[asyncio.subprocess.Process] = None

    async def _run(self, mojo: AsyncMojoStreamReader) -> None:
        # Start collecting samples
        self._state = AustinState.RUNNING

        async for e in mojo:
            if isinstance(e, AustinSample):
                try:
                    await t.cast(t.Awaitable[None], self._sample_callback(e))
                except Exception as exc:
                    raise AustinError("Error in call to sample callback") from exc
            elif isinstance(e, AustinMetadata):
                self._meta[e.name] = e.value
                if self._metadata_callback is not None:
                    try:
                        await t.cast(t.Awaitable[None], self._metadata_callback(e))
                    except Exception as exc:
                        raise AustinError("Error in call to metadata callback") from exc

        self._state = AustinState.TERMINATING

        # Call the terminate callback
        try:
            if self._terminate_callback is not None:
                await t.cast(t.Awaitable[None], self._terminate_callback())
        except Exception as exc:
            raise AustinError("Error in call to terminate callback") from exc

        self._state = AustinState.TERMINATED

    async def start(self, args: t.Optional[t.Sequence[str]] = None) -> None:
        """Create the start coroutine.

        Use with the ``asyncio`` event loop.
        """
        self._args = AustinArgumentParser().parse_args(args)

        self._state = AustinState.STARTING

        try:
            _args = list(args if args is not None else sys.argv[1:])  # Make a copy
            _args.insert(0, "-P")
            self._proc = await asyncio.create_subprocess_exec(
                self.binary_path,
                *_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            raise AustinError("Austin executable not found.") from None

        if not self._proc.stdout:
            raise AustinError("Standard output stream is unexpectedly missing")
        if not self._proc.stderr:
            raise AustinError("Standard error stream is unexpectedly missing")

        mojo = AsyncMojoStreamReader(self._proc.stdout)

        # Retrieve the Austin version, then call the ready callback
        async for e in mojo:
            if isinstance(e, AustinMetadata):
                self._meta[e.name] = e.value

                try:
                    if self._metadata_callback is not None:
                        await t.cast(t.Awaitable[None], self._metadata_callback(e))
                except Exception as exc:
                    raise AustinError("Error in call to metadata callback") from exc

                if e.name == "austin":
                    self._check_version()
                    break
        else:
            raise AustinError("Cannot determine Austin version from output")

        # Start the run task where we collect the samples
        self._run_task = asyncio.create_task(self._run(mojo))

    def terminate(self) -> None:
        """Terminate Austin.

        Stop the underlying Austin process by sending a termination signal.
        """
        if self._proc is None:
            raise AustinError("Austin is not running")

        try:
            self._proc.terminate()
        except ProcessLookupError as exc:
            raise AustinError("Austin process already terminated") from exc

    async def wait(self) -> int:
        if self._proc is None or self._run_task is None:
            raise AustinError("Austin process is not running")

        # Await the run task. This will terminate naturally when the Austin
        # process has terminated.
        await self._run_task

        # Wait for the Austin process to terminate and return the exit code
        return await self._proc.wait()
