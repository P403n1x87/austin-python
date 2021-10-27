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

from copy import deepcopy
import dataclasses
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
import re
from threading import Lock
from typing import Any, Dict, Generator, Iterator, List, Optional, TextIO, Type, Union

from austin import AustinError

# ---- Custom types ----
ThreadName = str
ProcessId = int
MicroSeconds = int
KiloBytes = int


# ---- Exceptions ----


class InvalidFrame(AustinError):
    """Invalid frame.

    Thrown when attempting to parse a string that is supposed to represent a
    frame, but has the wrong structure.
    """

    pass


class InvalidSample(AustinError):
    """Invalid sample.

    Thrown when attempting to parse a string that is supposed to represent a
    sample, but has the wrong structure.
    """

    pass


# ---- Dataclasses ----


class Metadata(dict):
    """Austin Metadata."""

    def add(self, line: str) -> None:
        """Add a metadata line."""
        assert line.startswith("# ")
        key, _, value = line[2:].partition(":")
        self[key] = value.strip()


class MetricType(Enum):
    """Sample metric type."""

    TIME = 0
    MEMORY = 1

    @classmethod
    def from_mode(cls, mode: str) -> Optional["MetricType"]:
        """Convert metadata mode to metric type."""
        return {
            "cpu": MetricType.TIME,
            "wall": MetricType.TIME,
            "memory": MetricType.MEMORY,
            "full": None,
        }.get(mode)


@dataclass(frozen=True)
class Metric:
    """Austin metrics."""

    type: MetricType
    value: Union[MicroSeconds, KiloBytes] = 0

    def __add__(self, other: "Metric") -> "Metric":
        """Add metrics together (algebraically)."""
        assert self.type == other.type
        return Metric(
            type=self.type,
            value=self.value + other.value,
        )

    def __sub__(self, other: "Metric") -> "Metric":
        """Subtract metrics (algebraically)."""
        assert self.type == other.type
        return Metric(
            type=self.type,
            value=self.value - other.value,
        )

    def __gt__(self, other: "Metric") -> bool:
        """Strict comparison of metrics."""
        assert self.type == other.type
        return self.value > other.value

    def __ge__(self, other: "Metric") -> bool:
        """Comparison of metrics."""
        assert self.type == other.type
        return self.value >= other.value

    def copy(self) -> "Metric":
        """Make a copy of this object."""
        return dataclasses.replace(self)

    @staticmethod
    def parse(metrics: str, metric_type: Optional[MetricType] = None) -> List["Metric"]:
        """Parse the metrics from a sample.

        Returns a tuple containing the parsed metrics and the head of the
        sample for further processing.
        """
        try:
            ms = [int(_) for _ in metrics.split(",")]
            if len(ms) == 3:
                return [
                    Metric(MetricType.TIME, ms[0] if ms[1] == 0 else 0),
                    Metric(MetricType.TIME, ms[0]),
                    Metric(MetricType.MEMORY, ms[2] if ms[2] >= 0 else 0),
                    Metric(MetricType.MEMORY, -ms[2] if ms[2] < 0 else 0),
                ]
            elif len(ms) != 1:
                raise ValueError()

            assert metric_type is not None

            return [Metric(metric_type, ms[0])]

        except ValueError:
            raise InvalidSample(metrics) from None

    def __str__(self) -> str:
        """Stringify the metric."""
        return str(self.value)


@dataclass(frozen=True)
class Frame:
    """Python frame."""

    function: str
    filename: str
    line: int = 0

    @staticmethod
    def parse(frame: str) -> "Frame":
        """Parse the given string as a frame.

        A string representing a frame has the structure

            ``[frame] := <module>:<function>:<line number>``

        This static method attempts to parse the given string in order to
        identify the parts of the frame and returns an instance of the
        :class:`Frame` dataclass with the corresponding fields filled in.
        """
        if not frame:
            raise InvalidFrame(frame)

        try:
            module, function, line = frame.rsplit(":", maxsplit=3)
        except ValueError:
            raise InvalidFrame(frame) from None
        return Frame(function, module, int(line))

    def __str__(self) -> str:
        """Stringify the ``Frame`` object."""
        return f"{self.filename}:{self.function}:{self.line}"


@dataclass
class Sample:
    """Austin sample."""

    pid: ProcessId
    thread: ThreadName
    metric: Metric
    frames: List[Frame] = field(default_factory=list)

    _ALT_FORMAT_RE = re.compile(r";L([0-9]+)")

    @staticmethod
    def is_full(sample: str) -> bool:
        """Determine whether the sample has full metrics."""
        try:
            _, _, metrics = sample.rpartition(" ")
            return len(metrics.split(",")) == 3
        except (ValueError, IndexError):
            return False

    @staticmethod
    def parse(sample: str, metric_type: Optional[MetricType] = None) -> List["Sample"]:
        """Parse the given string as a frame.

        A string representing a sample has the structure

            ``P<pid>;T<tid>[;[frame]]* [metric][,[metric]]*``

        This static method attempts to parse the given string in order to
        identify the parts of the sample and returns an instance of the
        :class:`Sample` dataclass with the corresponding fields filled in.
        """
        if not sample:
            raise InvalidSample(sample)

        if sample[0] != "P":
            raise InvalidSample(f"No process ID in sample '{sample}'")

        head, _, metrics = sample.rpartition(" ")
        process, _, rest = head.partition(";")
        try:
            pid = int(process[1:])
        except ValueError:
            raise InvalidSample(f"Invalid process ID in sample '{sample}'") from None

        if rest[0] != "T":
            raise InvalidSample(f"No thread ID in sample '{sample}'")

        thread, _, frames = rest.partition(";")
        thread = thread[1:]

        if frames:
            if frames.rfind(";L"):
                frames = Sample._ALT_FORMAT_RE.sub(r":\1", frames)

        try:
            ms = Metric.parse(metrics, metric_type)
            return [
                Sample(
                    pid=int(pid),
                    thread=thread,
                    metric=metric,
                    frames=[Frame.parse(frame) for frame in frames.split(";")]
                    if frames
                    else [],
                )
                for metric in ms
            ]
        except ValueError as e:
            raise InvalidSample(f"Sample has invalid metric values: {sample}") from e
        except InvalidFrame as e:
            raise InvalidSample(f"Sample has invalid frames: {sample}") from e


@dataclass
class HierarchicalStats:
    """Base dataclass for representing hierarchical statistics.

    The statistics of a frame stack can be thought of as a rooted tree. Hence
    the hierarchy is established by the parent/child relation between the
    nodes in this tree. An instance of this class represents a node, and a
    leaf is given by those instances with an empty ``children`` attribute.

    The ``label`` attribute is used for indexing reasons and therefore should
    be of a hashable type.

    This class overrides the default ``add`` operator so that one can perform
    operations like ``stats1 + stats2``. Note, however, that instances of this
    class are not assumed to be immutable and indeed this operation will modify
    and return ``stats1`` with the outcome of the addition.
    """

    label: Any
    own: Metric
    total: Metric
    children: Dict[Any, "HierarchicalStats"] = field(default_factory=dict)

    def __lshift__(self, other: "HierarchicalStats") -> "HierarchicalStats":
        """Merge the RHS into the LHS."""
        if self.label != other.label:
            return self

        self.own += other.own
        self.total += other.total

        for frame, child in other.children.items():
            try:
                self.children[frame] << child
            except KeyError:
                self.children[frame] = child

        return self

    def get_child(self, label: Any) -> "HierarchicalStats":
        """Get a child from the children collection."""
        return self.children[label]

    def collapse(self, prefix: str = "") -> List[str]:
        """Collapse the hierarchical statistics."""
        if not self.children:
            return [f";{prefix}{self.label} {self.own}"]

        own = (
            []
            if self.own == Metric(MetricType.TIME)
            else [f";{prefix}{self.label} {self.own}"]
        )
        return own + [
            f";{prefix}{self.label}{rest}"
            for _, child in self.children.items()
            for rest in child.collapse()
        ]


@dataclass
class FrameStats(HierarchicalStats):
    """Frame statistics."""

    label: Frame
    height: int = 0
    children: Dict[Frame, "FrameStats"] = field(default_factory=dict)  # type: ignore[assignment]


class ThreadStats(HierarchicalStats):
    """Thread statistics."""

    label: ThreadName
    children: Dict[Frame, FrameStats] = field(default_factory=dict)  # type: ignore[assignment]

    def collapse(self, prefix: str = "T") -> List[str]:
        """Collapse the hierarchical statistics."""
        return super().collapse(prefix)


@dataclass
class ProcessStats:
    """Process statistics."""

    pid: ProcessId
    threads: Dict[ThreadName, ThreadStats] = field(default_factory=dict)

    def collapse(self) -> List[str]:
        """Collapse the hierarchical statistics."""
        return [
            f"P{self.pid}{rest}"
            for _, thread in self.threads.items()
            for rest in thread.collapse()
        ]

    def get_thread(self, thread_name: ThreadName) -> Optional[ThreadStats]:
        """Get thread statistics from this process by name.

        If the given thread name is not registered with this current process
        statistics, then ``None`` is returned.
        """
        return self.threads.get(thread_name)


class AustinStatsType(Enum):
    """Austin stats type."""

    WALL = "wall"
    CPU = "cpu"
    MEMORY_ALLOC = "memory_alloc"
    MEMORY_DEALLOC = "memory_dealloc"


class AustinFileReader:
    """Austin file reader.

    Conveniently read an Austin sample file by also parsing any header and
    footer metadata.
    """

    def __init__(self, file: str) -> None:
        self.file = file
        self.metadata = Metadata()
        self._stream: Optional[TextIO] = None
        self._stream_iter: Optional[Iterator] = None

    def _read_meta(self) -> None:
        assert self._stream_iter is not None

        for line in self._stream_iter:
            if not line.startswith("# ") or line == "\n":
                break
            self.metadata.add(line)

    def __enter__(self) -> "AustinFileReader":
        """Open the Austin file and read the metadata."""
        self._stream = open(self.file, "r")
        self._stream_iter = iter(self._stream)

        self._read_meta()

        return self

    def __iter__(self) -> Iterator:
        """Iterator over the samples in the Austin file."""

        def _() -> Generator[str, None, None]:
            assert self._stream_iter is not None

            for line in self._stream_iter:
                if line == "\n":
                    break
                yield line

            self._read_meta()

        return _()

    def __exit__(self, *args: Any) -> None:
        """Close the Austin file."""
        assert self._stream is not None

        self._stream.close()


@dataclass
class AustinStats:
    """Austin statistics.

    This class is used to collect all the statistics about own and total time
    and/or memory generated by a run of Austin. The :func:`update` method is
    used to pass a new :class:`Sample` so that the statistics can be updated
    accordingly.
    """

    stats_type: AustinStatsType
    processes: Dict[ProcessId, ProcessStats] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, compare=False)

    def __deepcopy__(self, memo: Optional[Dict[Any, Any]] = None) -> "AustinStats":
        """Make a deep copy of this AustinStats object."""
        state = dict(self.__dict__)
        del state["_lock"]

        copy = type(self)(self.stats_type)
        copy.__dict__.update(deepcopy(state))

        return copy

    def dump(self, stream: TextIO) -> None:
        """Dump the statistics to the given text stream."""
        with self._lock:
            stream.write(f"# mode: {self.stats_type.value.partition('_')[0]}\n\n")
            for _, process in self.processes.items():
                samples = process.collapse()

                if all(sample.endswith(" 0 0") for sample in samples):
                    samples = [sample[:-4] for sample in samples]

                for sample in samples:
                    stream.write(sample + "\n")

    def get_process(self, pid: ProcessId) -> ProcessStats:
        """Get process statistics for the given PID."""
        return self.processes[pid]

    @classmethod
    def load(
        cls: Type["AustinStats"], stream: TextIO
    ) -> Dict[AustinStatsType, "AustinStats"]:
        """Load statistics from the given text stream."""
        meta = Metadata()
        for line in stream:
            if not line.startswith("# "):
                break
            meta.add(line)

        assert "mode" in meta
        metric_type = {
            "wall": MetricType.TIME,
            "cpu": MetricType.TIME,
            "memory": MetricType.MEMORY,
        }.get(meta["mode"])

        if metric_type is None:
            profiles = {
                AustinStatsType.CPU: AustinStats(AustinStatsType.CPU),
                AustinStatsType.WALL: AustinStats(AustinStatsType.WALL),
                AustinStatsType.MEMORY_ALLOC: AustinStats(AustinStatsType.MEMORY_ALLOC),
                AustinStatsType.MEMORY_DEALLOC: AustinStats(
                    AustinStatsType.MEMORY_DEALLOC
                ),
            }
        elif metric_type is MetricType.MEMORY:
            profiles = {
                AustinStatsType.MEMORY_ALLOC: AustinStats(AustinStatsType.MEMORY_ALLOC),
                AustinStatsType.MEMORY_DEALLOC: AustinStats(
                    AustinStatsType.MEMORY_DEALLOC
                ),
            }
        else:
            stats_type = (
                AustinStatsType.CPU if meta["mode"] == "cpu" else AustinStatsType.WALL
            )
            profiles = {stats_type: AustinStats(stats_type)}

        for line in stream:
            try:
                samples = Sample.parse(line, metric_type)
            except InvalidSample:
                continue

            if metric_type is None:
                cpu, wall, memory_alloc, memory_dealloc = samples

                profiles[AustinStatsType.WALL].update(wall)
                profiles[AustinStatsType.CPU].update(cpu)
                profiles[AustinStatsType.MEMORY_ALLOC].update(memory_alloc)
                profiles[AustinStatsType.MEMORY_DEALLOC].update(memory_dealloc)

            elif metric_type is MetricType.MEMORY:
                memory_alloc, memory_dealloc = samples

                profiles[AustinStatsType.MEMORY_ALLOC].update(memory_alloc)
                profiles[AustinStatsType.MEMORY_DEALLOC].update(memory_dealloc)

            else:
                profiles[stats_type].update(samples[0])

        return profiles

    def update(self, sample: Sample) -> None:
        """Update the statistics with a new sample.

        Normally, you would what to generate a new instance of :class:`Sample`
        by using :func:`Sample.parse` on a sample string passed by Austin to
        the sample callback.
        """
        zero = Metric(sample.metric.type, 0)
        pid = sample.pid
        thread_stats = ThreadStats(sample.thread, own=zero, total=sample.metric)

        # Convert the list of frames into a nested FrameStats instance
        stats: HierarchicalStats = thread_stats
        container = thread_stats.children
        for height, frame in enumerate(sample.frames):
            stats = FrameStats(
                label=frame, height=height, own=zero, total=sample.metric
            )
            container[frame] = stats
            container = stats.children
        stats.own = stats.total.copy()

        with self._lock:
            if pid not in self.processes:
                self.processes[pid] = ProcessStats(pid, {sample.thread: thread_stats})
                return

            process = self.processes[pid]
            if sample.thread not in process.threads:
                process.threads[sample.thread] = thread_stats
                return

            process.threads[sample.thread] << thread_stats
