# This file is part of "austin-python" which is released under GPL.
#
# See file LICENCE or go to http://www.gnu.org/licenses/ for full license
# details.
#
# austin-python is a Python wrapper around Austin, the CPython frame stack
# sampler.
#
# Copyright (c) 2018-2025 Gabriele N. Tornetta <phoenix1987@gmail.com>.
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

import typing as t
from argparse import ArgumentParser
from pathlib import Path
from traceback import print_exc

from austin.format.mojo import MojoEvent
from austin.format.mojo import MojoStreamReader


__version__ = "0.1.0"


def mojodbg(mojo: MojoStreamReader, echo: bool = False) -> None:
    offset = 4
    last_event_data: t.Tuple[t.Optional[MojoEvent], int] = (None, 0)
    try:
        for e in mojo.parse():
            if echo:
                print(e)
            last_event_data = (e, offset)
            offset = mojo._offset + 1
    except Exception as exc:
        last_event, last_event_offset = last_event_data

        print(f"Error at offset {offset:02x}: {exc}")
        print()
        print_exc()
        print()
        if last_event is not None:
            print(
                f"Last event {last_event} at {last_event_offset:02x}-{last_event_offset + len(last_event.raw):02x}"
            )
        print()
        base = last_event_offset & ~15  # Show the last 16 bytes from the last event
        mojo.hexdump(base, base + 64, {offset, last_event_offset})
    else:
        print("MOJO file parsed successfully.")


def main() -> None:
    argp = ArgumentParser(prog="mojodbg", description="Debug MOJO files.")

    argp.add_argument("input", type=Path, help="The MOJO file to debug.")
    argp.add_argument(
        "-e", "echo", action="store_true", help="Echo all the MOJO events"
    )
    argp.add_argument("-V", "--version", action="version", version=__version__)

    args = argp.parse_args()

    try:
        mojodbg(MojoStreamReader(args.input.expanduser().open("rb")), args.echo)
    except FileNotFoundError:
        print(f"No such input file: {args.input}")
        exit(2)
    except Exception as e:
        print(f"Unexpected error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
