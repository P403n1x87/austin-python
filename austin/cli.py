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

from argparse import ArgumentParser, Namespace, REMAINDER
from typing import Any, Callable, List, NoReturn

from austin import AustinError


class AustinCommandLineError(AustinError):
    """Invalid Austin command line."""

    pass


class AustinArgumentParser(ArgumentParser):
    """Austin Command Line parser.

    This command line parser is based on :class:`argparse.ArgumentParser` and
    provides a minimal implementation for parsing the standard Austin command
    line. The bool arguments of the constructor are used to specify whether
    the corresponding Austin option should be parsed or not. For example, if
    your application doesn't need the possiblity of switching to the
    alternative format, you can exclude this option with ``alt_format=False``.

    Note that al least one between ``pid`` and ``command`` is required, but
    they cannot be used together when invoking Austin.
    """

    def __init__(
        self,
        name: str = "austin",
        alt_format: bool = True,
        children: bool = True,
        exclude_empty: bool = True,
        exposure: bool = True,
        full: bool = True,
        interval: bool = True,
        memory: bool = True,
        pid: bool = True,
        sleepless: bool = True,
        timeout: bool = True,
        command: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(prog=name, **kwargs)

        def time(units: str) -> Callable[[str], int]:
            """Parse time argument with units."""
            base = {"us": 1, "ms": 1e3, "s": 1e6}[units]

            def parser(arg: str) -> int:
                if arg.endswith("us"):
                    return int(arg[:-2]) // base
                if arg.endswith("ms"):
                    return int(arg[:-2]) * 1000 // base
                if arg.endswith("s"):
                    return int(arg[:-1]) * 1000000 // base
                return int(arg)

            return parser

        if not (pid and command):
            raise AustinCommandLineError(
                "Austin command line parser must have at least one between pid "
                "and command."
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

        if exposure:
            self.add_argument(
                "-x",
                "--exposure",
                help="Sample for the given number of seconds only.",
                type=time("s"),
                default=None,
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
                help="Sampling interval (default is 100 μs).",
                type=time("us"),
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
                help="Approximate start up wait time. Increase on slow machines "
                "(default is 100 ms).",
                type=time("ms"),
            )

        if command:
            self.add_argument(
                "command",
                type=str,
                nargs=REMAINDER,
                help="The command to execute if no PID is provided, followed by "
                "its arguments.",
            )

    def parse_args(
        self, args: List[str] = None, namespace: Namespace = None
    ) -> Namespace:
        """Parse the list of arguments.

        Return a :class:`argparse.Namespace` with the parsed result. If no PID
        nor a command are passed, an instance of the
        :class:`AustinCommandLineError` exception is thrown.
        """
        parsed_austin_args, unparsed = super().parse_known_args(args, namespace)
        if unparsed:
            raise AustinCommandLineError(
                f"Some arguments were left unparsed: {unparsed}"
            )

        if not parsed_austin_args.pid and not parsed_austin_args.command:
            raise AustinCommandLineError("No PID or command given.")

        return parsed_austin_args

    def exit(self, status: int = 0, message: str = None) -> NoReturn:
        """Raise exception on error."""
        raise AustinCommandLineError(message, status)

    @staticmethod
    def to_list(args: Namespace) -> List[str]:
        """Convert a :class:`argparse.Namespace` to a list of arguments.

        This is the opposite of the parsing of the command line. This static
        method is intended to filter and reconstruct the command line arguments
        that need to be passed to lower level APIs to start the actual Austin
        process.
        """
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
            arg_list += args.command

        return arg_list
