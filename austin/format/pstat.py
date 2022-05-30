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

from pstats import Stats, add_func_stats
from austin.stats import AustinFileReader, MetricType, Sample, InvalidSample
import pathlib

from typing import Any, Dict, List, Union, Tuple


ProfileName = str


class Pstats:
    def __init__(self, austin_profile: Union[str, pathlib.Path]):
        self.last_stack = []
        self.stats: Dict[Tuple[str, int, str], Any] = {}
        self.callee_firstlineno: Dict[Tuple[str, str], int] = {}
        with AustinFileReader(austin_profile) as austin:
            assert "mode" in austin.metadata
            metric_type = {
                "wall": MetricType.TIME,
                "cpu": MetricType.TIME,
                "memory": MetricType.MEMORY,
            }.get(austin.metadata["mode"])
            for line in austin:
                try:
                    line_sample = Sample.parse(line, metric_type)
                    for metric_sample in line_sample:
                        if metric_sample.metric.type == MetricType.TIME:
                            self._add_time_sample(metric_sample)
                except InvalidSample:
                    continue
        self.python_stats: Stats = Stats(self)
        self.python_stats.get_top_level_stats()

    def print_stats(self, sort=-1):
        self.python_stats.strip_dirs().sort_stats(sort).print_stats()

    def dump(self, f):
        self.python_stats.dump_stats(f)

    def create_stats(self):
        pass

    def get_stats_profile(self):
        self.python_stats.get_stats_profile()

    def resolve_callee(self, co_filename: str, curlineno: int, co_name: str) -> Tuple[str, int, str]:
        """Normalise the callee lineno to be the first lineno, not the caller's lineno."""
        callsite = (co_filename, co_name)
        if callsite not in self.callee_firstlineno:
            self.callee_firstlineno[callsite] = curlineno
        
        return (co_filename, self.callee_firstlineno[callsite], co_name)

    def _add_time_sample(self, sample: Sample):
        # Stats.stats is a dictionary with key:
        #  (fcode.co_filename, fcode.co_firstlineno, fcode.co_name)
        # and value  (cc, ns, tt, ct, callers)
        #     [cc] = The number of times this function was called, not counting direct
        #           or indirect recursion,
        #     [ns] = Number of times this function appears on the stack, minus one
        #     [tt] = Total time spent internal to this function
        #     [ct] = Cumulative time that this function was present on the stack.  In
        #           non-recursive functions, this is the total execution time from start
        #           to finish of each invocation of a function, including time spent in
        #           all subfunctions.
        #     [callers] = A dictionary indicating for each function name, the number of times
        #           it was called by us.
        dt = sample.metric.value / 1_000_000
        frames = [(frame.filename, frame.line, frame.function) for frame in sample.frames]

        # Find the depth in the stack that changed between the last sample
        depth = None  # Default to stacks being identical
        for i, frame in enumerate(frames):
            try:
                if frames[i] != self.last_stack[i]:
                    depth = i
                    break
            except IndexError:
                depth = i
                break

        if not frames:
            # handle empty frames
            pass

        for callee, caller in zip(frames, [{}] + [{c: 1}  for c in frames[:-1]]):
            resolved_callee = self.resolve_callee(*callee)
            self.stats[resolved_callee] = add_func_stats(
                self.stats.get(resolved_callee, (1, 1, 0, 0, {})),
                (caller and 1 or 0, caller and 1 or 0, dt, dt, caller),
            )

        self.last_stack = frames

    def asdict(self):
        return self.python_stats.stats


def main() -> None:
    """austin2pstat entry point."""
    from argparse import ArgumentParser

    arg_parser = ArgumentParser(
        prog="austin2pstat",
        description=(
            "Convert Austin generated profiles to the cProfile pstat format. "
            "The output will contain a profile "
            "for each thread and metric included in the input file."
        ),
    )

    arg_parser.add_argument(
        "input",
        type=str,
        help="The input file containing Austin samples in normal format.",
    )
    arg_parser.add_argument(
        "output", type=str, help="The name of the output pstat file."
    )

    arg_parser.add_argument("-V", "--version", action="version", version="0.1.0")

    args = arg_parser.parse_args()

    try:
        stats = Pstats(args.input)

    except FileNotFoundError:
        print(f"No such input file: {args.input}")
        exit(1)

    stats.dump(args.output)
    stats.print_stats()


if __name__ == "__main__":
    main()
