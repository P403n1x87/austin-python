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

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
import json
from typing import Dict, List, Optional, TextIO, Union

from austin.format import Mode
from austin.stats import AustinFileReader
from austin.stats import Frame
from austin.stats import InvalidSample
from austin.stats import MetricType
from austin.stats import Sample

SpeedscopeJson = Dict
SpeedscopeWeight = int
ProfileName = str


class Units(Enum):
    """Metric units."""

    MICROSECONDS = "μs"
    BYTES = "bytes"


@dataclass(frozen=True)
class SpeedscopeFrame:
    """Speedscope Frame object."""

    name: str
    file: str
    line: int


@dataclass
class SpeedscopeProfile:
    """Speedscope Profile object."""

    name: ProfileName
    unit: str
    startValue: int = 0
    endValue: int = 0
    samples: List[List[int]] = field(default_factory=list)
    weights: List[SpeedscopeWeight] = field(default_factory=list)
    type: str = "sampled"

    def add_sample(self, stack: List[int], weight: SpeedscopeWeight) -> None:
        """Add a sample to the profile."""
        self.samples.append(stack)
        self.weights.append(weight)
        self.endValue += weight


class Speedscope:
    """Speedscope JSON generator."""

    def __init__(
        self, name: str, mode: Union[Mode, str], indent: Optional[int] = None
    ) -> None:
        self.name = name
        self.indent = indent
        self.mode = mode
        self.mode = Mode.from_metadata(mode) if isinstance(mode, str) else mode

        self.profiles: List[SpeedscopeProfile] = []
        self.profile_map: Dict[int, Dict[str, Dict[str, SpeedscopeProfile]]] = {}

        self.frames: List[dict] = []
        self.frame_map: Dict[Frame, int] = {}

    def get_frame(self, frame: Frame) -> int:
        """Get the index of an observed frame."""
        if frame in self.frame_map:
            return self.frame_map[frame]

        index = len(self.frames)
        self.frame_map[frame] = index
        self.frames.append(
            asdict(SpeedscopeFrame(frame.function, frame.filename, frame.line))
        )

        return index

    def get_profile(self, pid: int, thread: str, metric: str) -> SpeedscopeProfile:
        """Get the profile for the given pid, thread and profile metric."""
        prefix = {
            "cpu": "CPU time",
            "wall": "Wall time",
            "m+": "Memory allocation",
            "m-": "Memory deallocation",
        }[metric]
        units = Units.BYTES if metric[0] == "m" else Units.MICROSECONDS
        profiles = self.profile_map.setdefault(pid, {}).setdefault(thread, {})
        if metric in profiles:
            return profiles[metric]

        self.profiles.append(
            SpeedscopeProfile(
                name=f"{prefix} profile for {pid}:{thread}",
                unit=units.value,
            )
        )
        return profiles.setdefault(
            metric,
            self.profiles[-1],
        )

    def add_samples(self, samples: List[Sample]) -> None:
        """Add a sample to the generator."""
        if self.mode == Mode.CPU:
            _ = zip(("cpu",), samples)
        elif self.mode == Mode.WALL:
            _ = zip(("cpu",), samples)
        elif self.mode == Mode.MEMORY:
            _ = zip(("m+", "m-"), samples)
        elif self.mode == Mode.FULL:
            _ = zip(("cpu", "wall", "m+", "m-"), samples)

        for prefix, sample in _:
            if not sample.frames or sample.metric.value == 0:
                continue

            self.get_profile(sample.pid, sample.thread, prefix).add_sample(
                [self.get_frame(frame) for frame in sample.frames], sample.metric.value
            )

    def asdict(self) -> SpeedscopeJson:
        """Return the JSON as a Python dictionary."""
        return {
            "$schema": "https://www.speedscope.app/file-format-schema.json",
            "shared": {"frames": self.frames},
            "profiles": sorted(
                [asdict(profile) for profile in self.profiles],
                key=lambda p: p["name"].rsplit(maxsplit=1)[-1],
            ),
            "name": self.name,
            "exporter": "Austin2Speedscope Converter 0.2.0",
        }

    def dump(self, stream: TextIO) -> None:
        """Dump the pprof protobuf message to the given binary stream."""
        json.dump(
            self.asdict(),
            stream,
            indent=self.indent,
        )


def main() -> None:
    """austin2speedscope entry point."""
    from argparse import ArgumentParser
    import os

    arg_parser = ArgumentParser(
        prog="austin2speedscope",
        description=(
            "Convert Austin generated profiles to the Speedscope JSON format "
            "accepted by https://speedscope.app. The output will contain a profile "
            "for each thread and metric included in the input file."
        ),
    )

    arg_parser.add_argument(
        "input",
        type=str,
        help="The input file containing Austin samples in normal format.",
    )
    arg_parser.add_argument(
        "output", type=str, help="The name of the output Speedscope JSON file."
    )
    arg_parser.add_argument(
        "--indent", type=int, help="Give a non-null value to prettify the JSON output."
    )

    arg_parser.add_argument("-V", "--version", action="version", version="0.1.0")

    args = arg_parser.parse_args()

    try:
        with AustinFileReader(args.input) as fin:
            mode = fin.metadata["mode"]
            speedscope = Speedscope(os.path.basename(args.input), mode, args.indent)
            for line in fin:
                try:
                    speedscope.add_samples(
                        Sample.parse(line, MetricType.from_mode(mode))
                    )
                except InvalidSample:
                    continue

    except FileNotFoundError:
        print(f"No such input file: {args.input}")
        exit(1)

    with open(args.output, "w") as fout:
        speedscope.dump(fout)


if __name__ == "__main__":
    main()
