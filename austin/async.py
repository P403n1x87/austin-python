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

from austin import AustinError, BaseAustin


class AsyncAustin(BaseAustin):
    def __init__(self, sample_callback=None):
        super().__init__(sample_callback)
        self.start_event = asyncio.Event()

    def start(self, args, loop=None):
        async def _start():
            try:
                self.proc = await asyncio.create_subprocess_exec(
                    "austin",
                    *AustinArgumentParser.to_list(args),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
            except FileNotFoundError:
                raise AustinError("Executable not found.")

            self.post_process_start()

            # Signal that we are good to go
            self.start_event.set()
            self._running = True

            # Start readline loop
            while True:
                data = await self.proc.stdout.readline()
                if not data:
                    break
                self._callback(data.decode("ascii").rstrip())

            # Wait for the subprocess exit
            await self.proc.wait()
            self._running = False

        try:
            if args.pid is not None:
                self._pid = args.pid
        except AttributeError:
            self._pid = -1

        if not loop:
            if sys.platform == "win32":
                self._loop = asyncio.ProactorEventLoop()
                asyncio.set_event_loop(loop)
            else:
                self._loop = asyncio.get_event_loop()
        else:
            self._loop = loop

        self._start_task = self._loop.create_task(_start())

    def get_event_loop(self):
        return self._loop

    def wait(self, timeout=1):
        try:
            self._loop.run_until_complete(
                asyncio.wait_for(self.start_event.wait(), timeout)
            )
        except asyncio.TimeoutError:
            return False

        return True

    def join(self):
        try:
            return self._loop.run_until_complete(self._start_task)
        except asyncio.CancelledError:
            pass


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
