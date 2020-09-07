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

from austin.format.pprof import PProf
from austin.stats import InvalidSample, Sample


def main() -> None:
    """austin2pprof entry point."""
    arg_parser = ArgumentParser(
        prog="austin2pprof",
        description=(
            "Convert Austin generated profiles to the pprof protobuf format. "
            "See https://github.com/google/pprof for more details."
        ),
    )

    arg_parser.add_argument(
        "input", type=str, help="The input file containing Austin samples.",
    )
    arg_parser.add_argument(
        "output", type=str, help="The name of the output pprof file."
    )

    arg_parser.add_argument("-V", "--version", action="version", version="0.1.0")

    args = arg_parser.parse_args()

    pprof = PProf()

    try:
        with open(args.input, "r") as fin:
            for line in fin:
                try:
                    pprof.add_sample(Sample.parse(line))
                except InvalidSample:
                    continue

    except FileNotFoundError:
        print(f"No such input file: {args.input}")
        exit(1)

    with open(args.output, "wb") as fout:
        pprof.dump(fout)


if __name__ == "__main__":
    main()
