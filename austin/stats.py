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
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from threading import Lock
from typing import Any
from typing import Dict
from typing import Generator
from typing import List
from typing import Optional
from typing import Tuple

from austin.events import AustinEventIterator
from austin.events import AustinFrame
from austin.events import AustinMetadata
from austin.events import AustinMetrics
from austin.events import AustinSample
from austin.events import ProcessId
from austin.events import ThreadName
from austin.format.collapsed_stack import AustinEventCollapsedStackFormatter


COLLAPSED_STACK_FORMATTER = AustinEventCollapsedStackFormatter()


class AustinStatsType(Enum):
    """Austin stats type."""

    WALL = "wall"
    CPU = "cpu"
    MEMORY_ALLOC = "memory_alloc"
    MEMORY_DEALLOC = "memory_dealloc"


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
    own: int
    total: int
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

    def collapse(self, stats_type: AustinStatsType) -> Generator[Any, None, None]:
        """Collapse the hierarchical statistics."""
        raise NotImplementedError()


@dataclass
class FrameStats(HierarchicalStats):
    """Frame statistics."""

    label: AustinFrame
    height: int = 0
    children: Dict[AustinFrame, "FrameStats"] = field(default_factory=dict)  # type: ignore[assignment]

    def collapse(
        self, stats_type: AustinStatsType
    ) -> Generator[Tuple[List[AustinFrame], AustinMetrics], None, None]:
        """Collapse the hierarchical statistics."""
        frame = self.label

        if self.own:
            yield (
                [frame],
                AustinMetrics(time=self.own)
                if stats_type in {AustinStatsType.CPU, AustinStatsType.WALL}
                else AustinMetrics(memory=self.own),
            )

        if self.children:
            yield from (
                ([frame, *rest], metric)
                for child in self.children.values()
                for rest, metric in child.collapse(stats_type)
            )


class ThreadStats(HierarchicalStats):
    """Thread statistics."""

    label: ThreadName
    children: Dict[AustinFrame, FrameStats] = field(default_factory=dict)  # type: ignore[assignment]

    def collapse(
        self, stats_type: AustinStatsType
    ) -> Generator[Tuple[ThreadName, List[AustinFrame], AustinMetrics], None, None]:
        """Collapse the hierarchical statistics."""

        if self.own:
            yield (
                self.label,
                [],
                AustinMetrics(time=self.own)
                if stats_type in {AustinStatsType.CPU, AustinStatsType.WALL}
                else AustinMetrics(memory=self.own),
            )

        if self.children:
            yield from (
                (self.label, frames, metric)
                for stats in self.children.values()
                for frames, metric in stats.collapse(stats_type)
            )


@dataclass
class ProcessStats:
    """Process statistics."""

    pid: ProcessId
    threads: Dict[ThreadName, ThreadStats] = field(default_factory=dict)

    def collapse(
        self, stats_type: AustinStatsType
    ) -> Generator[AustinSample, None, None]:
        """Collapse the hierarchical statistics."""
        yield from (
            AustinSample(
                pid=self.pid,
                iid=thread_name.iid,
                thread=thread_name.thread,
                frames=tuple(frames),
                metrics=metric,
            )
            for thread in self.threads.values()
            for thread_name, frames, metric in thread.collapse(stats_type)
        )

    def get_thread(self, thread_name: ThreadName) -> Optional[ThreadStats]:
        """Get thread statistics from this process by name.

        If the given thread name is not registered with this current process
        statistics, then ``None`` is returned.
        """
        return self.threads.get(thread_name)


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

    def get_process(self, pid: ProcessId) -> ProcessStats:
        """Get process statistics for the given PID."""
        return self.processes[pid]

    @classmethod
    def load(cls, stream: AustinEventIterator) -> Dict[AustinStatsType, "AustinStats"]:
        """Load statistics from the given text stream."""
        mode = None
        for e in stream:
            if isinstance(e, AustinMetadata) and e.name == "mode":
                mode = e.value
                break
        else:
            raise ValueError("No mode metadata found in the stream")

        if mode == "full":
            profiles = {
                AustinStatsType.CPU: AustinStats(AustinStatsType.CPU),
                AustinStatsType.WALL: AustinStats(AustinStatsType.WALL),
                AustinStatsType.MEMORY_ALLOC: AustinStats(AustinStatsType.MEMORY_ALLOC),
                AustinStatsType.MEMORY_DEALLOC: AustinStats(
                    AustinStatsType.MEMORY_DEALLOC
                ),
            }
        elif mode == "memory":
            profiles = {
                AustinStatsType.MEMORY_ALLOC: AustinStats(AustinStatsType.MEMORY_ALLOC),
                AustinStatsType.MEMORY_DEALLOC: AustinStats(
                    AustinStatsType.MEMORY_DEALLOC
                ),
            }
        else:
            stats_type = AustinStatsType.CPU if mode == "cpu" else AustinStatsType.WALL
            profiles = {stats_type: AustinStats(stats_type)}

        for e in (_ for _ in stream if isinstance(_, AustinSample)):
            for profile in profiles.values():
                profile.update(e)

        return profiles

    def update(self, sample: AustinSample) -> None:
        """Update the statistics with a new sample.

        Normally, you would what to generate a new instance of :class:`Sample`
        by using :func:`Sample.parse` on a sample string passed by Austin to
        the sample callback.
        """
        if self.stats_type in {AustinStatsType.WALL, AustinStatsType.CPU}:
            metric = sample.metrics.time
        elif (
            self.stats_type is AustinStatsType.MEMORY_ALLOC
            and sample.metrics.memory is not None
            and sample.metrics.memory > 0
        ):
            metric = sample.metrics.memory
        elif (
            self.stats_type is AustinStatsType.MEMORY_DEALLOC
            and sample.metrics.memory is not None
            and sample.metrics.memory < 0
        ):
            metric = -sample.metrics.memory
        else:
            return

        if metric is None or metric == 0:
            return

        pid = sample.pid
        thread_name = ThreadName(sample.thread, sample.iid or 0)
        thread_stats = ThreadStats(thread_name, own=0, total=metric)

        # Convert the list of frames into a nested FrameStats instance
        stats: HierarchicalStats = thread_stats
        container = thread_stats.children
        for height, frame in enumerate(sample.frames or []):
            stats = FrameStats(label=frame, height=height, own=0, total=metric)
            container[frame] = stats
            container = stats.children
        stats.own = stats.total

        with self._lock:
            if pid not in self.processes:
                self.processes[pid] = ProcessStats(pid, {thread_name: thread_stats})
                return

            process = self.processes[pid]
            if thread_name not in process.threads:
                process.threads[thread_name] = thread_stats
                return

            process.threads[thread_name] << thread_stats

    def flatten(self) -> Generator[AustinSample, None, None]:
        for process in self.processes.values():
            yield from process.collapse(self.stats_type)
