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

import json
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import TextIO
from typing import Union

from austin.events import AustinFrame
from austin.events import AustinMetadata
from austin.events import AustinSample
from austin.format import Mode
from austin.format.collapsed_stack import AustinFileReader
from austin.format.collapsed_stack import InvalidSample


__version__ = "0.3.1"

SpeedscopeJson = Dict
SpeedscopeWeight = int
ProfileName = str


class Units(Enum):
    """Metric units."""

    MICROSECONDS = "microseconds"
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
        self.frame_map: Dict[AustinFrame, int] = {}

    def get_frame(self, frame: AustinFrame) -> int:
        """Get the index of an observed frame."""
        if frame in self.frame_map:
            return self.frame_map[frame]

        index = len(self.frames)
        self.frame_map[frame] = index
        self.frames.append(
            asdict(SpeedscopeFrame(frame.function, frame.filename, frame.line))
        )

        return index

    def get_profile(
        self, pid: int, iid: Optional[int], thread: str, metric: str
    ) -> SpeedscopeProfile:
        """Get the profile for the given pid, thread and profile metric."""
        prefix = {
            "cpu": "CPU time",
            "wall": "Wall time",
            "m+": "Memory allocation",
            "m-": "Memory deallocation",
        }[metric]
        units = Units.BYTES if metric.startswith("m") else Units.MICROSECONDS
        thread_key = f"{iid}:{thread}" if iid is not None else thread
        profiles = self.profile_map.setdefault(pid, {}).setdefault(thread_key, {})
        if metric in profiles:
            return profiles[metric]

        self.profiles.append(
            SpeedscopeProfile(
                name=f"{prefix} profile for {pid}:{thread_key}",
                unit=units.value,
            )
        )
        return profiles.setdefault(
            metric,
            self.profiles[-1],
        )

    def add_sample(self, sample: AustinSample) -> None:
        """Add a sample to the generator."""
        if sample.frames is None:
            return

        if self.mode == Mode.CPU:
            _ = zip(("cpu",), (sample.metrics.time,))
        elif self.mode == Mode.WALL:
            _ = zip(("wall",), (sample.metrics.time,))
        elif self.mode == Mode.MEMORY:
            assert sample.metrics.memory is not None
            memory_alloc = sample.metrics.memory if sample.metrics.memory >= 0 else 0
            memory_dealloc = -sample.metrics.memory if sample.metrics.memory < 0 else 0
            _ = zip(("m+", "m-"), (memory_alloc, memory_dealloc))
        elif self.mode == Mode.FULL:
            assert sample.metrics.memory is not None
            wall_time = sample.metrics.time
            cpu_time = 0 if sample.idle else wall_time
            memory_alloc = sample.metrics.memory if sample.metrics.memory >= 0 else 0
            memory_dealloc = -sample.metrics.memory if sample.metrics.memory < 0 else 0
            _ = zip(
                ("cpu", "wall", "m+", "m-"),
                (cpu_time, wall_time, memory_alloc, memory_dealloc),
            )

        for prefix, metric in _:
            if metric == 0:
                continue
            self.get_profile(sample.pid, sample.iid, sample.thread, prefix).add_sample(
                [self.get_frame(frame) for frame in sample.frames], metric
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
            "exporter": f"Austin2Speedscope Converter {__version__}",
        }

    def dump(self, stream: TextIO) -> None:
        """Dump the JSON to a text stream."""
        json.dump(
            self.asdict(),
            stream,
            indent=self.indent,
        )


def main() -> None:
    """austin2speedscope entry point."""
    import os
    from argparse import ArgumentParser

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
        type=Path,
        help="The input file containing Austin samples in normal format.",
    )
    arg_parser.add_argument(
        "output", type=Path, help="The name of the output Speedscope JSON file."
    )
    arg_parser.add_argument(
        "--indent", type=int, help="Give a non-null value to prettify the JSON output."
    )

    arg_parser.add_argument("-V", "--version", action="version", version=__version__)

    args = arg_parser.parse_args()

    try:
        with args.input.open() as austin, AustinFileReader(austin) as fin:
            speedscope = None
            for event in fin:
                if isinstance(event, AustinMetadata):
                    if event.name == "mode":
                        speedscope = Speedscope(
                            os.path.basename(args.input), event.value, args.indent
                        )
                elif isinstance(event, AustinSample):
                    if speedscope is not None:
                        speedscope.add_sample(event)
                else:
                    raise ValueError("Invalid sample found in input file")

        if speedscope is None:
            raise RuntimeError("Invalid input file: no mode metadata found")

        with args.output.open("w") as fout:
            speedscope.dump(fout)

    except FileNotFoundError:
        print(f"No such input file: {args.input}")
        exit(1)


if __name__ == "__main__":
    main()
