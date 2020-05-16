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

from argparse import ArgumentParser

from austin import AustinError


class AustinCommandLineError(AustinError):
    pass


class AustinArgumentParser(ArgumentParser):
    def __init__(
        self,
        name="austin",
        alt_format=True,
        children=True,
        exclude_empty=True,
        full=True,
        interval=True,
        memory=True,
        pid=True,
        sleepless=True,
        timeout=True,
        command=True,
        **kwargs,
    ):
        super().__init__(prog=name, **kwargs)

        if bool(pid) != bool(command):
            raise AustinCommandLineError(
                "Austin command line parser must have either pid or command."
            )

        if alt_format:
            self.add_argument(
                "-a",
                "--alt-format",
                help="Alternative collapsed stack sample format.",
                action="store_true",
            )

        if children:
            self.add_argument(
                "-C",
                "--children",
                help="Attach to child processes.",
                action="store_true",
            )

        if exclude_empty:
            self.add_argument(
                "-e",
                "--exclude-empty",
                help="Do not output samples of threads with no frame stacks.",
                action="store_true",
            )

        if full:
            self.add_argument(
                "-f",
                "--full",
                help="Produce the full set of metrics (time +mem -mem).",
                action="store_true",
            )

        if interval:
            self.add_argument(
                "-i",
                "--interval",
                help="Sampling interval (default is 100us).",
                type=int,
            )

        if memory:
            self.add_argument(
                "-m", "--memory", help="Profile memory usage.", action="store_true"
            )

        if pid:
            self.add_argument(
                "-p",
                "--pid",
                help="The the ID of the process to which Austin should attach.",
                type=int,
            )

        if sleepless:
            self.add_argument(
                "-s", "--sleepless", help="Suppress idle samples.", action="store_true"
            )

        if timeout:
            self.add_argument(
                "-t",
                "--timeout",
                help="Approximate start up wait time. Increase on slow machines (default is 100ms).",
                type=int,
            )

        if command:
            self.add_argument(
                "command",
                nargs="?",
                help="The command to execute if no PID is provided, followed by its arguments.",
            )

            self.add_argument(
                "args", nargs="*", help="Arguments to pass to the command to run."
            )

    def parse_args(self, args):
        parsed_args = super().parse_args(args)

        if not parsed_args.pid and not parsed_args.command:
            raise AustinCommandLineError("No PID or command given.")

        return parsed_args

    @staticmethod
    def to_list(args):
        arg_list = []
        if getattr(args, "alt_format", None):
            arg_list.append("-a")
        if getattr(args, "children", None):
            arg_list.append("-C")
        if getattr(args, "exclude_empty", None):
            arg_list.append("-e")
        if getattr(args, "full", None):
            arg_list.append("-f")
        if getattr(args, "interval", None):
            arg_list += ["-i", str(args.interval)]
        if getattr(args, "memory", None):
            arg_list.append("-m")
        if getattr(args, "pid", None):
            arg_list += ["-p", str(args.pid)]
        if getattr(args, "sleepless", None):
            arg_list.append("-s")
        if getattr(args, "timeout", None):
            arg_list += ["-t", str(args.timeout)]
        if getattr(args, "command", None):
            arg_list.append(args.command)
        if getattr(args, "args", None):
            arg_list += args.args

        return arg_list
