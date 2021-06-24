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

from typing import Any, BinaryIO, Dict, List, Tuple, Union

from austin.format import Mode
from austin.format.pprof.profile_pb2 import Profile
from austin.format.pprof.profile_pb2 import Sample
from austin.stats import Frame
from austin.stats import Sample as AustinSample

PROCESS_ID_LABEL = "Process ID"
THREAD_ID_LABEL = "Thread ID"

CPU_TYPE = "CPU time"
WALL_TYPE = "Wall time"
TIME_UNIT = "μs"

MEMORY_ALLOC_TYPE = "Allocated memory"
MEMORY_DEALLOC_TYPE = "Deallocated memory"
MEMORY_UNIT = "B"


class PProf:
    """PProf generator class.

    Used to convert Austin collapsed format into the pprof protobuf format.
    """

    def __init__(self, mode: Union[Mode, str]) -> None:
        self._string_table: Dict[str, int] = {}
        self._location_map: Dict[Frame, int] = {}
        self._function_map: Dict[Tuple[str, str], int] = {}

        # Create the protobuf Profile message
        self.profile = Profile()
        self.profile.string_table.append("")

        # Add sample types according to the mode
        if isinstance(mode, str):
            mode = Mode.from_metadata(mode)

        if mode == Mode.MEMORY:
            self._add_memory_sample_types()

        elif mode == Mode.CPU:
            self._add_time_sample_type(CPU_TYPE)

        elif mode == Mode.WALL:
            self._add_time_sample_type(WALL_TYPE)

        elif mode == Mode.FULL:
            self._add_time_sample_type(CPU_TYPE)
            self._add_time_sample_type(WALL_TYPE)
            self._add_memory_sample_types()

        self.mode = mode

    def _add_sample_type(self, type: str, unit: str) -> None:
        _ = self.profile.sample_type.add()
        _.type = self.get_string(type)
        _.unit = self.get_string(unit)

    def _add_time_sample_type(self, type: str) -> None:
        self._add_sample_type(type, TIME_UNIT)

    def _add_memory_sample_types(self) -> None:
        self._add_sample_type(MEMORY_ALLOC_TYPE, MEMORY_UNIT)
        self._add_sample_type(MEMORY_DEALLOC_TYPE, MEMORY_UNIT)

    def get_string(self, string: str) -> int:
        """Get the string table index for the given string."""
        try:
            return self._string_table[string]
        except KeyError:
            index = len(self.profile.string_table)
            self._string_table[string] = index
            self.profile.string_table.append(string)
            return index

    def add_label_to_sample(self, sample: Sample, key: Any, value: Any) -> None:
        """Add a sample label to the given sample.

        The ``key`` and ``value`` arguments are both converted to strings.
        """
        _ = sample.label.add()
        _.key = self.get_string(str(key))
        _.str = self.get_string(str(value))

    def get_function(self, frame: Frame) -> int:
        """Get the function id from the given Austin frame."""
        key = (frame.function, frame.filename)
        try:
            return self._function_map[key]
        except KeyError:
            function = self.profile.function.add()
            function.id = len(self.profile.function)
            function.name = self.get_string(frame.function)
            function.filename = self.get_string(frame.filename)

            self._function_map[key] = function.id

            return function.id

    def get_location(self, frame: Frame) -> int:
        """Get the location id from the given Austin frame."""
        try:
            return self._location_map[frame]
        except KeyError:
            location = self.profile.location.add()
            location.id = len(self.profile.location)
            line = location.line.add()
            line.function_id = self.get_function(frame)
            line.line = frame.line

            self._location_map[frame] = location.id

            return location.id

    def add_samples(self, samples: List[AustinSample]) -> None:
        """Add a sample to the pprof generator."""
        # Create new pprof sample
        pprof_sample = self.profile.sample.add()

        # Add process and thread id labels
        self.add_label_to_sample(pprof_sample, THREAD_ID_LABEL, samples[0].thread)
        self.add_label_to_sample(pprof_sample, PROCESS_ID_LABEL, samples[0].pid)

        # Add metrics
        for sample in samples:
            pprof_sample.value.append(sample.metric.value)

        # Add locations. Top of the stack first.
        for frame in samples[0].frames[::-1]:
            pprof_sample.location_id.append(self.get_location(frame))

    def dump(self, stream: BinaryIO) -> None:
        """Dump the pprof protobuf message to the given binary stream."""
        stream.write(self.profile.SerializeToString())
