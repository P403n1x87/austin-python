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
from threading import Event, Thread

import psutil

from austin import AustinError, BaseAustin


class ThreadedAustin(BaseAustin, Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        Thread.__init__(self)

        self.start_event = Event()

    def run(self):
        self.start_event.set()
        self._running = True

        while True:
            line = self.proc.stdout.readline()
            if not line:
                break
            self._callback(line.decode("ascii").rstrip())

        self.proc.wait()
        self._running = False

    def start(self, args):
        try:
            self._pid = args.pid
        except AttributeError:
            self._pid = -1

        self.proc = subprocess.Popen(["austin"] + args, stdout=subprocess.PIPE)

        try:
            self.post_process_start()
        except psutil.NoSuchProcess as e:
            raise AustinError("Unable to start Austin.") from e

        Thread.start(self)

    def wait(self, timeout=1):
        self.start_event.wait(timeout)

    def join(self):
        self.proc.wait()


# ---- TEST ----

if __name__ == "__main__":

    class MyThreadedAustin(ThreadedAustin):
        def on_sample_received(self, line):
            print(line)

    try:
        austin = MyThreadedAustin()
        austin.start(["-i", "10000", "python3", "test/target34.py"])
        austin.join()
    except KeyboardInterrupt:
        print("Bye!")
