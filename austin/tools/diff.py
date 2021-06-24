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
from difflib import SequenceMatcher
from io import StringIO
from typing import List, Set, TextIO, Tuple

from austin.format.compress import compress
from austin.stats import Frame
from austin.stats import InvalidSample
from austin.stats import Metric
from austin.stats import Sample

FoldedStack = List[Frame]


def _similarities(
    x: List[FoldedStack], y: List[FoldedStack]
) -> List[Tuple[Tuple[int, int], float]]:
    """O(n * log(n)), n = len(x) * len(y)."""

    def score(a: List[Frame], b: List[Frame]) -> float:
        """Score two folded stacks."""
        if not len(a) and not len(b):
            return 1
        return SequenceMatcher(a=a, b=b).ratio() - abs(len(a) - len(b)) / (
            len(a) + len(b)
        )

    return sorted(
        [((i, j), score(a, b)) for i, a in enumerate(x) for j, b in enumerate(y)],
        key=lambda x: x[1],
        reverse=True,
    )


def _match(
    x: List[FoldedStack], y: List[FoldedStack], threshold: float = 0.0
) -> Set[Tuple[int, int]]:
    """O(len(x) * len(y))."""
    ss = _similarities(x, y)
    mx, my = set(), set()
    matches = set()
    for (i, j), s in ss:
        if i in mx or j in my or s <= threshold:
            continue
        mx.add(i)
        my.add(j)
        matches.add((i, j))
    return matches


def diff(a: TextIO, b: TextIO) -> str:
    """Compare stacks and return a - b.

    The algorithm attempts to match stacks that look similar and returns
    only positive time differences (that is, stacks of b that took longer
    than those in a are not reported), plus any new stacks that are not in
    b.

    The return value is a string with collapsed stacks followed by the delta
    of the metrics on each line.
    """

    def compressed(source: TextIO) -> str:
        """Compress the source."""
        _ = StringIO()
        compress(source, _)
        return _.getvalue()

    def get_frames(text: str) -> List[Tuple[FoldedStack, Metric]]:
        """Get the folded stacks and metrics from a string of samples."""
        x = []
        for _ in text.splitlines(keepends=False):
            try:
                sample = Sample.parse(_)
                x.append((sample.frames, sample.metrics))
            except InvalidSample:
                continue
        return x

    fa = get_frames(compressed(a))
    fb = get_frames(compressed(b))
    ms = _match([frames for frames, _ in fa], [frames for frames, _ in fb])

    matched = set()
    stacks = []
    time_only = True

    # Matched stacks
    for i, j in ms:
        matched.add(i)
        delta = fa[i][1] - fb[j][1]
        if delta >= 0:
            stacks.append((fa[i][0], delta))
        if delta.memory_alloc or delta.memory_dealloc:
            time_only = False

    # New stacks
    for i in [_ for _ in range(len(fa)) if _ not in matched]:
        f, m = fa[i]
        stacks.append((f, m))

    return "\n".join(
        [
            ";".join([str(_) for _ in f]) + " " + str(m.time if time_only else m)
            for f, m in stacks
        ]
    )


def main() -> None:
    """Diff tool for Austin samples."""
    argp = ArgumentParser(
        prog="austin-diff",
        description=("Compute the diff between two austin frame stack sample files"),
    )

    argp.add_argument("a", type=str, help="The minuend collapsed stacks")
    argp.add_argument("b", type=str, help="The subtrahend collapsed stacks")
    argp.add_argument("-o", "--output", type=str, help="The output file")
    argp.add_argument("-V", "--version", action="version", version="0.1.0")

    args = argp.parse_args()

    with open(args.a) as a, open(args.b) as b:
        result = diff(a, b)
        if args.output is not None:
            with open(args.output, "w") as fout:
                fout.write(result)
        else:
            print(result)


if __name__ == "__main__":
    main()
