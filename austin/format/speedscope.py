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

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
from typing import Any, Dict, Iterator, List, Tuple

from austin.stats import InvalidSample, Sample

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
    unit: Units
    startValue: int = 0
    endValue: int = 0
    samples: List[Any] = field(default_factory=list)
    weights: List[SpeedscopeWeight] = field(default_factory=list)
    type: str = "sampled"


def _generate_profiles(
    source: Iterator[str]
) -> Tuple[List[SpeedscopeFrame], Dict[ProfileName, SpeedscopeProfile]]:
    shared_frames: List[SpeedscopeFrame] = []
    frame_index = {}

    profiles = {}

    def get_profile(name: ProfileName, unit: Units) -> SpeedscopeProfile:
        if name not in profiles:
            profiles[name] = SpeedscopeProfile(name=name, unit=unit.value)

        return profiles[name]

    def add_frames_to_thread_profile(
        thread_profile: SpeedscopeProfile, sample: Sample, metric: SpeedscopeWeight
    ) -> None:
        stack = []
        for frame in sample.frames:
            frame_id = str(frame)
            if frame_id not in frame_index:
                frame_index[frame_id] = len(shared_frames)
                shared_frames.append(
                    SpeedscopeFrame(frame.function, frame.filename, frame.line)
                )

            stack.append(frame_index[frame_id])

        thread_profile.samples.append(stack)
        thread_profile.weights.append(metric)
        thread_profile.endValue += metric

    for line in source:
        try:
            sample = Sample.parse(line)
        except InvalidSample:
            continue

        thread = f"Thread {sample.pid}:{sample.thread.split()[1]}"

        add_frames_to_thread_profile(
            get_profile(f"Time profile of {thread}", Units.MICROSECONDS),
            sample,
            sample.metrics.time,
        )

        if sample.metrics.memory_alloc:
            add_frames_to_thread_profile(
                get_profile(f"Memory allocation profile of {thread}", Units.BYTES),
                sample,
                sample.metrics.memory_alloc << 10,
            )

        if sample.metrics.memory_dealloc:
            add_frames_to_thread_profile(
                get_profile(f"Memory release profile of {thread}", Units.BYTES),
                sample,
                sample.metrics.memory_dealloc << 10,
            )

    return shared_frames, profiles


def _generate_json(
    frames: List[SpeedscopeFrame],
    profiles: Dict[ProfileName, SpeedscopeProfile],
    name: str,
) -> SpeedscopeJson:
    return {
        "$schema": "https://www.speedscope.app/file-format-schema.json",
        "shared": {"frames": [asdict(frame) for frame in frames]},
        "profiles": sorted(
            [asdict(profile) for _, profile in profiles.items()],
            key=lambda p: p["name"].rsplit(maxsplit=1)[-1],
        ),
        "name": name,
        "exporter": "Austin2Speedscope Converter 0.2.0",
    }


def to_speedscope(source: Iterator[str], name: str) -> SpeedscopeJson:
    """Convert a list of collapsed samples to the speedscope JSON format.

    The result is a Python ``dict`` that complies with the Speedscope JSON
    schema and that can be exported to a JSON file with a straight call to
    ``json.dump``.

    Returns:
        (dict): a dictionary that complies with the speedscope JSON schema.
    """
    return _generate_json(*_generate_profiles(source), name)


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
        with open(args.input, "r") as fin:
            json.dump(
                to_speedscope(fin, os.path.basename(args.input)),
                open(args.output, "w"),
                indent=args.indent,
            )
    except FileNotFoundError:
        print(f"No such input file: {args.input}")
        exit(1)


if __name__ == "__main__":
    main()
