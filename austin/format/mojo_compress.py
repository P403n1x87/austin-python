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

import typing as t
from io import BytesIO

from austin.events import AustinMetadata
from austin.events import AustinMetrics
from austin.events import AustinSample
from austin.format.mojo import MojoStreamReader
from austin.format.mojo import MojoStreamWriter


def compress(source: t.BinaryIO, dest: t.BinaryIO) -> None:
    """Compress a MOJO source stream.

    Aggregates all metrics on equal stacks, where equality is determined by
    pid, interpreter id, thread, frames, gc flag, and idle flag.
    """
    time_stats: t.Dict[AustinSample.Key, int] = {}
    memory_stats: t.Dict[AustinSample.Key, int] = {}
    metadata: t.List[AustinMetadata] = []
    samples: t.Dict[AustinSample.Key, AustinSample] = {}

    reader = MojoStreamReader(source)

    for event in reader:
        if isinstance(event, AustinMetadata):
            metadata.append(event)
            continue

        assert isinstance(event, AustinSample)

        key = event.key()
        if key not in samples:
            samples[key] = event
        if event.metrics.time is not None:
            time_stats[key] = time_stats.get(key, 0) + event.metrics.time
        if event.metrics.memory is not None:
            memory_stats[key] = memory_stats.get(key, 0) + event.metrics.memory

    writer = MojoStreamWriter(dest)

    for m in metadata:
        writer.write(m)

    for key in samples:
        writer.write(
            AustinSample.from_key_and_metrics(
                key,
                AustinMetrics(
                    time=time_stats.get(key),
                    memory=memory_stats.get(key),
                ),
            )
        )


def main() -> None:
    """mojo-compress entry point."""
    from argparse import ArgumentParser

    arg_parser = ArgumentParser(
        prog="mojo-compress",
        description=(
            "Compress a MOJO sample file by aggregating the collected samples."
        ),
    )

    arg_parser.add_argument(
        "input",
        type=str,
        help="The input MOJO file.",
    )
    arg_parser.add_argument(
        "output",
        type=str,
        help="The output MOJO file; defaults to the input file for in-place compression.",
        nargs="?",
        default=None,
    )

    arg_parser.add_argument("-V", "--version", action="version", version="0.1.0")

    args = arg_parser.parse_args()

    try:
        with open(args.input, "rb") as fin:
            buffer = BytesIO()
            compress(fin, buffer)

        output_path = args.output or args.input
        with open(output_path, "wb") as fout:
            fout.write(buffer.getvalue())

    except FileNotFoundError:
        print(f"No such input file: {args.input}")
        exit(1)


if __name__ == "__main__":
    main()
