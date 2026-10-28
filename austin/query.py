# This file is part of "austin-python" which is released under GPL.
#
# See file LICENCE or go to http://www.gnu.org/licenses/ for full license
# details.
#
# austin-python is a Python wrapper around Austin, the CPython frame stack
# sampler.
#
# Copyright (c) 2018-2026 Gabriele N. Tornetta <phoenix1987@gmail.com>.
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

"""Query Austin profiles.

The :class:`ProfileQuery` class takes the events produced by any Austin event
iterator (e.g. a MOJO or a collapsed stack file reader) and answers the most
common questions about a profile, such as which functions are the hottest, what
the sampled stacks are, or who calls a given function::

    from austin.query import ProfileQuery

    q = ProfileQuery.from_file("profile.mojo")
    print(q.summary())
    print(q.top(10))
    print(q.callers("db.py:execute"))
    print(q.filter(thread="main").tree(min_pct=5))

Every query returns a result object that renders as a compact text table when
printed, and that can be converted to JSON-ready data with ``to_dict()``.

Frames are referred to by *selectors*. A selector is either

- a string of the form ``function``, ``file:function`` or
  ``file:function:line``, where ``file`` matches any path suffix and
  ``function`` also matches qualified names ending in ``.function``;
- a string ``re:<pattern>``, matched against ``file:function:line``;
- a :class:`Location` or an :class:`austin.events.AustinFrame`;
- a predicate over :class:`austin.events.AustinFrame` objects.

When a selector matches more than one function, the query aggregates over all
of them and reports what it matched.

Totals are recursion-safe: a function that appears more than once in a stack
counts that stack only once.

In asyncio profiles, the stack of a sample in which a task was running is the
thread stack followed by the running task's frames, i.e. the stack of the code
that was actually running. Use :meth:`ProfileQuery.tasks` for the task tree, and
the ``task`` filter for the samples in which a given task was running.

Rendered results show shortened file paths, relative to the ``pythonpath``,
``cwd`` and ``venv`` metadata when the profile has them, or to the
``site-packages`` and standard library folders otherwise. Shortened paths are
still valid selectors. The data returned by ``to_dict()`` uses full paths.
"""

import gc
import re
import typing as t
from collections import Counter
from collections import defaultdict
from copy import copy
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from dataclasses import is_dataclass
from dataclasses import replace
from difflib import get_close_matches
from pathlib import Path

from austin.events import AustinEvent
from austin.events import AustinFrame
from austin.events import AustinMetadata
from austin.events import AustinSample
from austin.events import AustinTask
from austin.events import ProcessId
from austin.events import ThreadName
from austin.format.collapsed_stack import AustinFileReader
from austin.format.mojo import MojoStreamReader
from austin.stats import AustinStats
from austin.stats import AustinStatsType
from austin.stats import FrameStats
from austin.stats import HierarchicalStats
from austin.stats import ThreadStats
from austin.stats import sample_metric

TIME_METRICS = frozenset({AustinStatsType.WALL, AustinStatsType.CPU})

MODE_METRICS: t.Dict[str, t.Tuple[AustinStatsType, ...]] = {
    "wall": (AustinStatsType.WALL,),
    "cpu": (AustinStatsType.CPU,),
    "memory": (AustinStatsType.MEMORY_ALLOC, AustinStatsType.MEMORY_DEALLOC),
    "full": (
        AustinStatsType.WALL,
        AustinStatsType.CPU,
        AustinStatsType.MEMORY_ALLOC,
        AustinStatsType.MEMORY_DEALLOC,
    ),
}

METRIC_ALIASES: t.Dict[str, AustinStatsType] = {
    **{_.value: _ for _ in AustinStatsType},
    "memory": AustinStatsType.MEMORY_ALLOC,
    "alloc": AustinStatsType.MEMORY_ALLOC,
    "dealloc": AustinStatsType.MEMORY_DEALLOC,
}


@dataclass(frozen=True)
class Location:
    """A code location.

    The ``line`` is ``None`` when the location refers to a whole function. The
    string representation can be used as a selector.
    """

    filename: str
    function: str
    line: t.Optional[int] = None

    def __str__(self) -> str:
        """Render as text."""
        if not self.filename:
            return self.function
        if self.line is None:
            return f"{self.filename}:{self.function}"
        return f"{self.filename}:{self.function}:{self.line}"

    @classmethod
    def from_frame(cls, frame: AustinFrame, lines: bool = False) -> "Location":
        """Get the location of a frame, optionally with line granularity."""
        return cls(frame.filename, frame.function, frame.line if lines else None)


# Pseudo-locations
#: The caller of the outermost frames
ROOT = Location("", "<root>")
#: The own share of a function among its callees
SELF = Location("", "<self>")
ALL = Location("", "<all>")  # The root of a call tree over the whole profile

Selector = t.Union[str, Location, AustinFrame, t.Callable[[AustinFrame], bool]]
FrameMatcher = t.Callable[[AustinFrame], bool]
TaskSelector = t.Union[int, str, t.Callable[[AustinTask], bool]]


class NoMatchError(LookupError):
    """Raised when a selector does not match any frame."""


def _is_path(s: str) -> bool:
    return "/" in s or "\\" in s or s.endswith(".py")


def _parse_selector(
    selector: str,
) -> t.Tuple[t.Optional[str], t.Optional[str], t.Optional[int]]:
    """Split a string selector into file, function and line parts."""
    line = None
    head, sep, tail = selector.rpartition(":")
    if sep and tail.isdigit():
        line = int(tail)
        selector = head
        head, sep, tail = selector.rpartition(":")

    if sep and tail and not _is_path(tail):
        return head or None, tail, line

    # No function part, e.g. "app/db.py" or "C:\app\db.py"
    if _is_path(selector):
        return selector, None, line

    return None, selector, line


def matcher(selector: Selector) -> FrameMatcher:
    """Turn a selector into a frame predicate."""
    if isinstance(selector, AustinFrame):
        selector = Location.from_frame(selector, lines=True)

    if isinstance(selector, Location):
        location = selector
        return lambda f: (
            f.filename == location.filename
            and f.function == location.function
            and (location.line is None or f.line == location.line)
        )

    if not isinstance(selector, str):
        return selector

    if selector.startswith("re:"):
        pattern = re.compile(selector[3:])
        return lambda f: (
            pattern.search(f"{f.filename}:{f.function}:{f.line}") is not None
        )

    filename, function, line = _parse_selector(selector)

    def match(frame: AustinFrame) -> bool:
        if filename is not None and not (
            frame.filename == filename
            or frame.filename.endswith(("/" + filename, "\\" + filename))
        ):
            return False
        if function is not None and not (
            frame.function == function or frame.function.endswith("." + function)
        ):
            return False
        return line is None or frame.line == line

    return match


SITE_PACKAGES_ROOT = re.compile(r"^(.*[/\\](?:site|dist)-packages)[/\\]")
STDLIB_ROOT = re.compile(r"^(.*[/\\](?:lib[/\\]python\d+(?:\.\d+)?t?|Lib))[/\\]")
WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:[/\\]")


def _is_absolute(path: str) -> bool:
    return path.startswith(("/", "\\")) or WINDOWS_DRIVE.match(path) is not None


def _is_path_suffix(suffix: str, path: str) -> bool:
    return path == suffix or path.endswith(("/" + suffix, "\\" + suffix))


class PathShortener:
    """Shorten file paths for display.

    Each path is made relative to the longest root that contains it. Roots are
    the ``pythonpath`` entries, the ``cwd`` and the ``venv`` from the profile
    metadata, when available, and the ``site-packages`` and standard library
    folders of Python source files. Shortened paths are then extended as needed
    so that none of them is a path suffix of another file, which makes them
    usable as selectors.
    """

    def __init__(
        self, filenames: t.Iterable[str], metadata: t.Mapping[str, str]
    ) -> None:
        cwd = metadata.get("cwd")
        pythonpath = metadata.get("pythonpath", "")
        sep = ";" if ";" in pythonpath or WINDOWS_DRIVE.match(pythonpath) else ":"

        roots = []
        for entry in filter(None, pythonpath.split(sep)):
            if _is_absolute(entry):
                roots.append(entry)
            elif cwd:
                dirsep = "\\" if "\\" in cwd else "/"
                roots.append(cwd.rstrip(dirsep) + dirsep + entry)
        roots.extend(_ for _ in (cwd, metadata.get("venv")) if _)
        self._roots = [r.rstrip("/\\") for r in roots if r.rstrip("/\\")]

        short = {f: self._strip(f) for f in set(filenames)}

        by_basename: t.Dict[str, t.List[str]] = defaultdict(list)
        for f in short:
            by_basename[re.split(r"[/\\]", f)[-1]].append(f)
        for group in by_basename.values():
            for f in group if len(group) > 1 else ():
                s = short[f]
                while s != f and any(_is_path_suffix(s, g) for g in group if g != f):
                    start = len(f) - len(s) - 1  # The separator before s
                    s = f[max(f.rfind("/", 0, start), f.rfind("\\", 0, start)) + 1 :]
                short[f] = s

        self._short = short

    def _strip(self, filename: str) -> str:
        root = ""
        for r in self._roots:
            if (
                len(r) > len(root)
                and filename.startswith(r)
                and filename[len(r) : len(r) + 1] in {"/", "\\"}
            ):
                root = r
        if filename.endswith(".py"):
            for pattern in (SITE_PACKAGES_ROOT, STDLIB_ROOT):
                m = pattern.match(filename)
                if m is not None and len(m.group(1)) > len(root):
                    root = m.group(1)
        return filename[len(root) + 1 :] if root else filename

    def __call__(self, filename: str) -> str:
        """Shorten a file path."""
        return self._short.get(filename, filename)


def _keep_path(filename: str) -> str:
    return filename


def _format_value(value: int, metric: AustinStatsType) -> str:
    if metric in TIME_METRICS:
        if value < 1_000:
            return f"{value}µs"
        if value < 1_000_000:
            return f"{value / 1e3:.1f}ms"
        return f"{value / 1e6:.2f}s"

    for unit in ("B", "KiB", "MiB"):
        if value < 1024:
            return f"{value:.0f}{unit}" if unit == "B" else f"{value:.1f}{unit}"
        value /= 1024  # type: ignore[assignment]
    return f"{value:.1f}GiB"


def _pct(value: int, total: int) -> float:
    return 100 * value / total if total else 0.0


def _jsonable(obj: t.Any) -> t.Any:
    if isinstance(obj, Location):
        return str(obj)
    if isinstance(obj, AustinStatsType):
        return obj.value
    if isinstance(obj, float):
        return round(obj, 2)
    if is_dataclass(obj) and not isinstance(obj, type):
        return {
            f.name: _jsonable(getattr(obj, f.name))
            for f in fields(obj)
            if f.metadata.get("json", True)
        }
    if isinstance(obj, (list, tuple)):
        return [_jsonable(_) for _ in obj]
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    return obj


def _table(header: t.Sequence[str], rows: t.Iterable[t.Sequence[str]]) -> str:
    """Render a table with right-aligned columns, except for the last one."""
    rows = [header, *rows]
    widths = [max(len(row[i]) for row in rows) for i in range(len(header) - 1)]
    return "\n".join(
        "  ".join([*(c.rjust(w) for c, w in zip(row, widths)), row[-1]]).rstrip()
        for row in rows
    )


@dataclass(frozen=True)
class _Result:
    """Base class for query results."""

    metric: AustinStatsType
    profile_total: int
    profile_samples: int
    paths: t.Callable[[str], str] = field(
        default=_keep_path,
        compare=False,
        repr=False,
        kw_only=True,
        metadata={"json": False},
    )

    def fmt(self, value: int) -> str:
        """Format a metric value with its unit."""
        return _format_value(value, self.metric)

    def label(self, location: Location) -> str:
        """Format a location with a shortened path."""
        if not location.filename:
            return str(location)
        return str(
            Location(self.paths(location.filename), location.function, location.line)
        )

    def header(self, *extra: str) -> str:
        return " · ".join(
            (
                f"metric: {self.metric.value}",
                f"total: {self.fmt(self.profile_total)}",
                f"samples: {self.profile_samples:,}",
                *extra,
            )
        )

    def render(self) -> str:
        """Render the result as text."""
        raise NotImplementedError()

    def __str__(self) -> str:
        """Render as text."""
        return self.render()

    def to_dict(self) -> t.Dict[str, t.Any]:
        """Convert the result to JSON-ready data."""
        return _jsonable(self)


@dataclass(frozen=True)
class TopEntry:
    """Own and total metric values of a location."""

    location: Location
    own: int
    total: int
    own_samples: int
    total_samples: int
    own_pct: float
    total_pct: float


@dataclass(frozen=True)
class TopResult(_Result):
    """A list of locations with their own and total metric values."""

    entries: t.Tuple[TopEntry, ...]
    matched: t.Tuple[Location, ...] = ()

    def __iter__(self) -> t.Iterator[TopEntry]:
        """Iterate over the entries."""
        return iter(self.entries)

    def __len__(self) -> int:
        """Return the number of entries."""
        return len(self.entries)

    def __getitem__(self, i: int) -> TopEntry:
        """Get an entry by index."""
        return self.entries[i]

    def render(self) -> str:
        extra = (f"matched: {len(self.matched)}",) if self.matched else ()
        return "\n".join(
            (
                self.header(*extra),
                _table(
                    ("own", "own%", "total", "total%", "samples", "location"),
                    (
                        (
                            self.fmt(e.own),
                            f"{e.own_pct:.1f}%",
                            self.fmt(e.total),
                            f"{e.total_pct:.1f}%",
                            f"{e.total_samples:,}",
                            self.label(e.location),
                        )
                        for e in self.entries
                    ),
                ),
            )
        )


@dataclass(frozen=True)
class Stack:
    """A distinct stack, root first, with its own metric value.

    The ``pid`` and ``thread`` are only set when stacks are kept separate per
    thread.
    """

    frames: t.Tuple[Location, ...]
    value: int
    samples: int
    pct: float
    pid: t.Optional[ProcessId] = None
    thread: t.Optional[ThreadName] = None


@dataclass(frozen=True)
class StacksResult(_Result):
    """A list of distinct stacks, heaviest first."""

    entries: t.Tuple[Stack, ...]
    count: int  # Number of distinct stacks before truncation

    def __iter__(self) -> t.Iterator[Stack]:
        """Iterate over the entries."""
        return iter(self.entries)

    def __len__(self) -> int:
        """Return the number of entries."""
        return len(self.entries)

    def __getitem__(self, i: int) -> Stack:
        """Get an entry by index."""
        return self.entries[i]

    def render(self) -> str:
        lines = [self.header(f"stacks: {len(self.entries):,} of {self.count:,}")]
        for stack in self.entries:
            where = (
                f"  [pid {stack.pid}, thread {stack.thread}]"
                if stack.thread is not None
                else ""
            )
            lines.append(
                f"\n{self.fmt(stack.value)}  {stack.pct:.1f}%  "
                f"({stack.samples:,} samples){where}"
            )
            lines.extend(f"  {self.label(frame)}" for frame in stack.frames)
            if not stack.frames:
                lines.append("  <no frames>")
        return "\n".join(lines)


@dataclass(frozen=True)
class Edge:
    """A caller or callee of the matched frames.

    The ``pct`` is relative to the profile total, the ``share`` to the total of
    the matched frames.
    """

    location: Location
    value: int
    samples: int
    pct: float
    share: float


@dataclass(frozen=True)
class Neighbours(_Result):
    """The callers or callees of the matched frames.

    Callers include :data:`ROOT` when the matched frames are the outermost in a
    stack. Callees include :data:`SELF` for the own value of the matched frames.
    """

    kind: str  # "callers" or "callees"
    matched: t.Tuple[Location, ...]
    own: int
    total: int
    samples: int
    entries: t.Tuple[Edge, ...]

    def __iter__(self) -> t.Iterator[Edge]:
        """Iterate over the entries."""
        return iter(self.entries)

    def __len__(self) -> int:
        """Return the number of entries."""
        return len(self.entries)

    def __getitem__(self, i: int) -> Edge:
        """Get an entry by index."""
        return self.entries[i]

    def render(self) -> str:
        target = (
            self.label(self.matched[0])
            if len(self.matched) == 1
            else f"{len(self.matched)} locations"
        )
        lines = [
            self.header(),
            f"{self.kind} of {target} · "
            f"own: {self.fmt(self.own)} ({_pct(self.own, self.profile_total):.1f}%) · "
            f"total: {self.fmt(self.total)} "
            f"({_pct(self.total, self.profile_total):.1f}%) · "
            f"samples: {self.samples:,}",
        ]
        if len(self.matched) > 1:
            lines.extend(f"  matched: {self.label(m)}" for m in self.matched)
        lines.append(
            _table(
                ("value", "pct", "share", "samples", "location"),
                (
                    (
                        self.fmt(e.value),
                        f"{e.pct:.1f}%",
                        f"{e.share:.1f}%",
                        f"{e.samples:,}",
                        self.label(e.location),
                    )
                    for e in self.entries
                ),
            )
        )
        return "\n".join(lines)


@dataclass
class CallNode:
    """A node in a call tree."""

    location: Location
    own: int
    total: int
    samples: int
    pct: float
    children: t.List["CallNode"] = field(default_factory=list)


@dataclass(frozen=True)
class CallTree(_Result):
    """A call tree, merged across processes and threads.

    Children below the ``min_pct`` threshold, or deeper than ``max_depth``, are
    pruned.
    """

    root: CallNode
    matched: t.Tuple[Location, ...] = ()

    def render(self) -> str:
        extra = (f"matched: {len(self.matched)}",) if self.matched else ()
        rows = []
        stack = [(self.root, 0)]
        while stack:
            node, depth = stack.pop()
            rows.append(
                (
                    self.fmt(node.total),
                    f"{node.pct:.1f}%",
                    self.fmt(node.own),
                    "  " * depth + self.label(node.location),
                )
            )
            stack.extend((c, depth + 1) for c in reversed(node.children))
        return "\n".join(
            (self.header(*extra), _table(("total", "total%", "own", "location"), rows))
        )

    def to_dict(self) -> t.Dict[str, t.Any]:
        # Convert the tree iteratively, as it can be deeper than the recursion
        # limit.
        data: t.Dict[str, t.Any] = {
            "metric": self.metric.value,
            "profile_total": self.profile_total,
            "profile_samples": self.profile_samples,
            "matched": _jsonable(self.matched),
        }

        def node_dict(node: CallNode) -> t.Dict[str, t.Any]:
            return {
                "location": str(node.location),
                "own": node.own,
                "total": node.total,
                "samples": node.samples,
                "pct": round(node.pct, 2),
                "children": [],
            }

        data["root"] = root = node_dict(self.root)
        stack = [(self.root, root)]
        while stack:
            node, d = stack.pop()
            for child in node.children:
                cd = node_dict(child)
                d["children"].append(cd)
                stack.append((child, cd))
        return data


@dataclass(frozen=True)
class MetricSummary:
    """The total of a metric over the profile."""

    metric: AustinStatsType
    total: int
    samples: int


@dataclass(frozen=True)
class ThreadSummary:
    """The total of the default metric for a thread."""

    pid: ProcessId
    iid: int
    thread: ThreadName
    total: int
    samples: int
    pct: float


@dataclass(frozen=True)
class Summary(_Result):
    """An overview of a profile."""

    mode: str
    metadata: t.Dict[str, str]
    metrics: t.Tuple[MetricSummary, ...]
    threads: t.Tuple[ThreadSummary, ...]

    def render(self) -> str:
        lines = [f"mode: {self.mode} · samples: {self.profile_samples:,}"]
        lines.extend(f"{k}: {v}" for k, v in self.metadata.items() if k != "mode")
        lines.append("")
        lines.append(
            _table(
                ("total", "samples", "metric"),
                (
                    (
                        _format_value(m.total, m.metric),
                        f"{m.samples:,}",
                        m.metric.value,
                    )
                    for m in self.metrics
                ),
            )
        )
        lines.append("")
        lines.append(f"threads by {self.metric.value}:")
        lines.append(
            _table(
                ("total", "pct", "samples", "pid", "iid", "thread"),
                (
                    (
                        self.fmt(th.total),
                        f"{th.pct:.1f}%",
                        f"{th.samples:,}",
                        str(th.pid),
                        str(th.iid),
                        th.thread,
                    )
                    for th in self.threads
                ),
            )
        )
        return "\n".join(lines)


@dataclass
class TaskNode:
    """A node in an asyncio task tree.

    ``running`` is the value of the samples in which the task was running, and
    ``awaiting`` the wall time it was alive without running, which is 0 for
    every other metric. In wall time, ``total`` is the time the task was alive,
    which already includes the time it spent awaiting its children. For every
    other metric, it is the value of the task and of every task it awaited.
    """

    task_id: int
    name: t.Optional[str]
    pid: ProcessId
    thread: ThreadName
    running: int
    awaiting: int
    total: int
    pct: float
    children: t.List["TaskNode"] = field(default_factory=list)


@dataclass(frozen=True)
class TasksResult(_Result):
    """The asyncio task trees of a profile, one per root task.

    A task is a child of the task that awaits it, and the roots are grouped by
    the thread that owns them.
    """

    roots: t.Tuple[TaskNode, ...]

    def __iter__(self) -> t.Iterator[TaskNode]:
        """Iterate over the root tasks."""
        return iter(self.roots)

    def __len__(self) -> int:
        """Return the number of root tasks."""
        return len(self.roots)

    def __getitem__(self, i: int) -> TaskNode:
        """Get a root task by index."""
        return self.roots[i]

    def render(self) -> str:
        wall = self.metric is AustinStatsType.WALL
        header = (
            "total",
            "total%",
            "running",
            *(("awaiting",) if wall else ()),
            "task",
        )
        rows = []
        where = None
        for root in self.roots:
            if (root.pid, root.thread) != where:
                where = (root.pid, root.thread)
                rows.append(
                    ("",) * (len(header) - 1)
                    + (f"[pid {root.pid}, thread {root.thread}]",)
                )
            stack = [(root, 0)]
            while stack:
                node, depth = stack.pop()
                name = node.name if node.name is not None else "<unnamed>"
                rows.append(
                    (
                        self.fmt(node.total),
                        f"{node.pct:.1f}%",
                        self.fmt(node.running),
                        *((self.fmt(node.awaiting),) if wall else ()),
                        "  " * depth + f"{name} #{node.task_id}",
                    )
                )
                stack.extend((c, depth + 1) for c in reversed(node.children))
        count = sum(1 for _ in self._nodes())
        return "\n".join((self.header(f"tasks: {count:,}"), _table(header, rows)))

    def _nodes(self) -> t.Iterator[TaskNode]:
        stack = list(self.roots)
        while stack:
            node = stack.pop()
            yield node
            stack.extend(node.children)


@dataclass(frozen=True)
class TaskStack:
    """A distinct task position, root first, with the value spent there.

    ``running`` is the value of the samples in which a task was running at the
    position, and ``awaiting`` the wall time a task was suspended there, which
    is 0 for every other metric. ``value`` is their sum.
    """

    frames: t.Tuple[Location, ...]
    value: int
    running: int
    awaiting: int
    samples: int
    pct: float


@dataclass(frozen=True)
class TaskStacksResult(_Result):
    """The positions of the matched tasks, heaviest first.

    Concurrent tasks are alive at the same time, so in wall time the values of
    their positions can add up to more than the profile total.
    """

    entries: t.Tuple[TaskStack, ...]
    count: int  # Number of distinct positions before truncation
    matched: t.Tuple[str, ...]  # The matched tasks, as "name #id"

    def __iter__(self) -> t.Iterator[TaskStack]:
        """Iterate over the entries."""
        return iter(self.entries)

    def __len__(self) -> int:
        """Return the number of entries."""
        return len(self.entries)

    def __getitem__(self, i: int) -> TaskStack:
        """Get an entry by index."""
        return self.entries[i]

    def render(self) -> str:
        wall = self.metric is AustinStatsType.WALL
        tasks = self.matched[0] if len(self.matched) == 1 else f"{len(self.matched):,}"
        lines = [
            self.header(
                f"tasks: {tasks}",
                f"positions: {len(self.entries):,} of {self.count:,}",
            )
        ]
        if wall and sum(e.value for e in self.entries) > self.profile_total:
            lines.append(
                "note: concurrent tasks overlap in time, so these values add up "
                "to more than the profile total"
            )
        for stack in self.entries:
            split = f"running {self.fmt(stack.running)}"
            if wall:
                split += f", awaiting {self.fmt(stack.awaiting)}"
            lines.append(
                f"\n{self.fmt(stack.value)}  {stack.pct:.1f}%  ({split}; "
                f"{stack.samples:,} samples)"
            )
            lines.extend(f"  {self.label(frame)}" for frame in stack.frames)
            if not stack.frames:
                lines.append("  <no frames>")
        return "\n".join(lines)


def _own_samples(node: HierarchicalStats) -> int:
    return node.samples - sum(c.samples for c in node.children.values())


def _walk(roots: t.Iterable[FrameStats]) -> t.Iterator[t.Tuple[FrameStats, bool]]:
    """Traverse the given stats trees depth-first.

    Each node is yielded as ``(node, True)`` on entry and ``(node, False)`` on
    exit. The traversal is iterative because stacks can be deeper than the recursion
    limit.
    """
    stack: t.List[t.Tuple[FrameStats, bool]] = [(r, True) for r in roots]
    while stack:
        node, entering = stack.pop()
        yield node, entering
        if entering:
            stack.append((node, False))
            stack.extend((c, True) for c in node.children.values())


def _matches_running(
    sample: AustinSample, match: t.Callable[[AustinTask], bool]
) -> bool:
    task = _running_task(sample)
    return task is not None and match(task)


def _iter_tasks(tasks: t.Iterable[AustinTask]) -> t.Iterator[AustinTask]:
    """Iterate over the tasks of task trees, waiters before the tasks they await."""
    stack = list(tasks)
    while stack:
        task = stack.pop()
        yield task
        stack.extend(task.awaiting)


def _running_task(sample: AustinSample) -> t.Optional[AustinTask]:
    """Get the task the thread of a sample was running, if any."""
    if sample.running_task is None:
        return None
    return next(
        (_ for _ in _iter_tasks(sample.tasks) if _.task_id == sample.running_task),
        None,
    )


def _stitch(sample: AustinSample) -> AustinSample:
    """Append the frames of the running task, if any, to the thread stack.

    Austin reports the frames of a running task as the task's position, not as
    part of its thread stack. Stitching them back gives the stack of the code
    that was actually running.
    """
    task = _running_task(sample)
    if task is None or not task.frames:
        return sample
    return replace(sample, frames=(*(sample.frames or ()), *task.frames))


def task_matcher(selector: TaskSelector) -> t.Callable[[AustinTask], bool]:
    """Turn a task selector into a task predicate.

    A task selector is a task ID, a task name, a string ``re:<pattern>``
    matched against task names, or a predicate over
    :class:`austin.events.AustinTask` objects.
    """
    if isinstance(selector, int):
        return lambda task: task.task_id == selector
    if not isinstance(selector, str):
        return selector
    if selector.startswith("re:"):
        pattern = re.compile(selector[3:])
        return lambda task: (
            task.name is not None and pattern.search(task.name) is not None
        )
    return lambda task: task.name == selector


class ProfileQuery:
    """Query an Austin profile.

    The profile is given as a stream of Austin events, e.g. from a
    ``austin.format.mojo.MojoStreamReader``. Queries take an optional
    ``metric``, which defaults to the metric of the profile mode, or wall time
    for full-mode profiles. Use :meth:`filter` to narrow a profile down before
    querying it. Percentages are relative to the total of the queried profile.
    Rendered results show shortened paths, unless ``short_paths`` is false.
    """

    def __init__(
        self, events: t.Iterable[AustinEvent], *, short_paths: bool = True
    ) -> None:
        self.metadata: t.Dict[str, str] = {}

        samples = []
        # Loading creates many objects, but no reference cycles, so the cyclic
        # garbage collector would only slow it down.
        gc_enabled = gc.isenabled()
        gc.disable()
        try:
            for event in events:
                if isinstance(event, AustinMetadata):
                    self.metadata[event.name] = event.value
                elif isinstance(event, AustinSample):
                    samples.append(_stitch(event))
        finally:
            if gc_enabled:
                gc.enable()
        self.samples: t.Tuple[AustinSample, ...] = tuple(samples)

        mode = self.metadata.get("mode")
        if mode not in MODE_METRICS:
            has_time = any(s.metrics.time is not None for s in self.samples)
            has_memory = any(s.metrics.memory is not None for s in self.samples)
            if has_time and has_memory:
                mode = "full"
            else:
                mode = "memory" if has_memory else "wall"
        self.mode: str = mode

        self._stats: t.Dict[AustinStatsType, AustinStats] = {}
        self._paths: t.Optional[t.Callable[[str], str]] = (
            None if short_paths else _keep_path
        )

    @property
    def paths(self) -> t.Callable[[str], str]:
        """The path shortener used to render results."""
        if self._paths is None:
            self._paths = PathShortener(
                (f.filename for s in self.samples for f in s.frames or ()),
                self.metadata,
            )
        return self._paths

    @classmethod
    def from_file(
        cls, path: t.Union[str, Path], *, short_paths: bool = True
    ) -> "ProfileQuery":
        """Load a profile from a MOJO or a collapsed stack file."""
        with open(path, "rb") as f:
            is_mojo = f.read(3) == b"MOJ"

        if is_mojo:
            with open(path, "rb") as f:
                return cls(MojoStreamReader(f), short_paths=short_paths)

        with open(path) as f:
            return cls(AustinFileReader(f), short_paths=short_paths)

    @property
    def metrics(self) -> t.Tuple[AustinStatsType, ...]:
        """The metrics available in the profile."""
        return MODE_METRICS[self.mode]

    def metric(
        self, metric: t.Union[None, str, AustinStatsType] = None
    ) -> AustinStatsType:
        """Resolve a metric name, defaulting to the metric of the profile."""
        if metric is None:
            return self.metrics[0]

        if isinstance(metric, str):
            try:
                metric = METRIC_ALIASES[metric.lower()]
            except KeyError:
                raise ValueError(
                    f"Unknown metric {metric!r}; "
                    f"expected one of {', '.join(sorted(METRIC_ALIASES))}"
                ) from None

        if metric not in self.metrics:
            raise ValueError(
                f"Metric {metric.value!r} not available in {self.mode} mode; "
                f"expected one of {', '.join(m.value for m in self.metrics)}"
            )

        return metric

    def stats(self, metric: t.Union[None, str, AustinStatsType] = None) -> AustinStats:
        """Get the aggregated statistics of the profile for a metric."""
        stats_type = self.metric(metric)
        try:
            return self._stats[stats_type]
        except KeyError:
            stats = self._stats[stats_type] = AustinStats(stats_type)

            # Most samples repeat a stack seen before, so merge each distinct
            # stack into the stats once, rather than once per sample.
            Key = t.Tuple[ProcessId, int, ThreadName, t.Tuple[AustinFrame, ...]]
            values: t.Dict[Key, t.List[int]] = {}
            for sample in self.samples:
                value = sample_metric(sample, stats_type)
                if not value:
                    continue
                key = (sample.pid, sample.iid or 0, sample.thread, sample.frames or ())
                try:
                    acc = values[key]
                except KeyError:
                    values[key] = [value, 1]
                else:
                    acc[0] += value
                    acc[1] += 1

            for (pid, iid, thread, frames), (value, samples) in values.items():
                stats.add_stack(pid, iid, thread, frames, value, samples)

            return stats

    def _threads(
        self, stats: AustinStats
    ) -> t.Iterator[t.Tuple[ProcessId, ThreadStats]]:
        for pid, process in stats.processes.items():
            for thread in process.threads.values():
                yield pid, thread

    def _roots(self, stats: AustinStats) -> t.Iterator[FrameStats]:
        for _, thread in self._threads(stats):
            yield from thread.children.values()

    def _totals(self, stats: AustinStats) -> t.Tuple[int, int]:
        total = samples = 0
        for _, thread in self._threads(stats):
            total += thread.total
            samples += thread.samples
        return total, samples

    def _no_match(self, selector: Selector) -> NoMatchError:
        message = f"No frames match {selector!r}"
        if isinstance(selector, str):
            _, function, _ = _parse_selector(selector.removeprefix("re:"))
            functions = {f.function for s in self.samples for f in s.frames or ()}
            candidates = {name.rpartition(".")[-1]: name for name in functions} | {
                name: name for name in functions
            }
            close = get_close_matches(function or selector, candidates, n=5)
            if close:
                names = sorted({candidates[_] for _ in close})
                message += f"; did you mean one of: {', '.join(names)}?"
        return NoMatchError(message)

    def _match_tasks(self, selector: TaskSelector) -> t.Callable[[AustinTask], bool]:
        """Get the predicate of a task selector, which must match some task."""
        match = task_matcher(selector)
        names: t.Set[str] = set()
        for sample in self.samples:
            for task in _iter_tasks(sample.tasks):
                if match(task):
                    return match
                if task.name is not None:
                    names.add(task.name)

        message = f"No tasks match {selector!r}"
        if not names:
            message += "; the profile has no asyncio tasks"
        elif isinstance(selector, str):
            close = get_close_matches(selector.removeprefix("re:"), names, n=5)
            if close:
                message += f"; did you mean one of: {', '.join(sorted(close))}?"
        raise NoMatchError(message)

    def filter(
        self,
        *,
        pid: t.Optional[ProcessId] = None,
        thread: t.Optional[ThreadName] = None,
        iid: t.Optional[int] = None,
        idle: t.Optional[bool] = None,
        gc: t.Optional[bool] = None,
        contains: t.Optional[Selector] = None,
        task: t.Optional[TaskSelector] = None,
        where: t.Optional[t.Callable[[AustinSample], bool]] = None,
    ) -> "ProfileQuery":
        """Narrow the profile down to the samples that match all the criteria.

        ``contains`` keeps the samples with at least one frame matching the
        given selector. ``task`` keeps the samples in which a task matching
        the given task selector (see :func:`task_matcher`) was running, and
        raises :class:`NoMatchError` if no task matches it. Use
        :meth:`task_stacks` to see where tasks were awaiting too.
        ``where`` is an arbitrary sample predicate.
        """
        match = matcher(contains) if contains is not None else None
        match_task = self._match_tasks(task) if task is not None else None

        def keep(s: AustinSample) -> bool:
            return (
                (pid is None or s.pid == pid)
                and (thread is None or s.thread == thread)
                and (iid is None or (s.iid or 0) == iid)
                and (idle is None or bool(s.idle) is idle)
                and (gc is None or bool(s.gc) is gc)
                and (match is None or any(match(f) for f in s.frames or ()))
                and (match_task is None or _matches_running(s, match_task))
                and (where is None or where(s))
            )

        query = copy(self)
        query._paths = self.paths  # Keep paths consistent with the full profile
        query.samples = tuple(s for s in self.samples if keep(s))
        query._stats = {}
        return query

    def summary(self) -> Summary:
        """Get an overview of the profile."""
        metric = self.metric()
        stats = self.stats(metric)
        total, samples = self._totals(stats)

        return Summary(
            paths=self.paths,
            metric=metric,
            profile_total=total,
            profile_samples=len(self.samples),
            mode=self.mode,
            metadata=dict(self.metadata),
            metrics=tuple(
                MetricSummary(m, *self._totals(self.stats(m))) for m in self.metrics
            ),
            threads=tuple(
                sorted(
                    (
                        ThreadSummary(
                            pid=pid,
                            iid=thread.label.iid,
                            thread=thread.label.thread,
                            total=thread.total,
                            samples=thread.samples,
                            pct=_pct(thread.total, total),
                        )
                        for pid, thread in self._threads(stats)
                    ),
                    key=lambda th: th.total,
                    reverse=True,
                )
            ),
        )

    def _flat(
        self,
        metric: t.Union[None, str, AustinStatsType],
        lines: bool,
        match: t.Optional[FrameMatcher] = None,
    ) -> t.Tuple[AustinStats, t.List[TopEntry], t.Set[Location]]:
        """Compute the own and total values of every (matching) location."""
        stats = self.stats(metric)
        profile_total, _ = self._totals(stats)

        own: t.Counter[Location] = Counter()
        own_samples: t.Counter[Location] = Counter()
        total: t.Counter[Location] = Counter()
        total_samples: t.Counter[Location] = Counter()
        matched: t.Set[Location] = set()

        path: t.Counter[Location] = Counter()
        for node, entering in _walk(self._roots(stats)):
            frame = node.label
            if match is not None and not match(frame):
                continue
            key = Location.from_frame(frame, lines)
            if not entering:
                path[key] -= 1
                continue
            if match is not None:
                matched.add(Location.from_frame(frame))
            own[key] += node.own
            own_samples[key] += _own_samples(node)
            if not path[key]:
                total[key] += node.total
                total_samples[key] += node.samples
            path[key] += 1

        entries = [
            TopEntry(
                location=key,
                own=own[key],
                total=total[key],
                own_samples=own_samples[key],
                total_samples=total_samples[key],
                own_pct=_pct(own[key], profile_total),
                total_pct=_pct(total[key], profile_total),
            )
            for key in total
        ]

        return stats, entries, matched

    def _top_result(
        self,
        stats: AustinStats,
        entries: t.Iterable[TopEntry],
        matched: t.Iterable[Location] = (),
    ) -> TopResult:
        total, samples = self._totals(stats)
        return TopResult(
            paths=self.paths,
            metric=stats.stats_type,
            profile_total=total,
            profile_samples=samples,
            entries=tuple(entries),
            matched=tuple(sorted(matched, key=str)),
        )

    def top(
        self,
        n: t.Optional[int] = 20,
        *,
        metric: t.Union[None, str, AustinStatsType] = None,
        by: str = "own",
        lines: bool = False,
    ) -> TopResult:
        """Get the top ``n`` locations by ``own`` or ``total`` value.

        Locations are functions, or lines if ``lines`` is true.
        """
        if by not in {"own", "total"}:
            raise ValueError(f"Invalid sort key {by!r}; expected 'own' or 'total'")

        stats, entries, _ = self._flat(metric, lines)
        entries.sort(key=lambda e: (getattr(e, by), e.total), reverse=True)
        return self._top_result(stats, entries[:n])

    def find(
        self,
        selector: Selector,
        *,
        metric: t.Union[None, str, AustinStatsType] = None,
        lines: bool = False,
    ) -> TopResult:
        """Find the locations that match a selector, heaviest first.

        Use this to check what a selector matches before passing it to other
        queries.
        """
        stats, entries, matched = self._flat(metric, lines, matcher(selector))
        entries.sort(key=lambda e: (e.total, e.own), reverse=True)
        return self._top_result(stats, entries, matched)

    def lines(
        self,
        selector: Selector,
        *,
        metric: t.Union[None, str, AustinStatsType] = None,
    ) -> TopResult:
        """Get the line breakdown of the matched functions, heaviest first.

        The own value of a line is the time (or memory) spent on the line
        itself, the total value also includes what it calls.
        """
        stats, entries, matched = self._flat(metric, True, matcher(selector))
        if not matched:
            raise self._no_match(selector)
        entries.sort(key=lambda e: (e.total, e.own), reverse=True)
        return self._top_result(stats, entries, matched)

    def stacks(
        self,
        n: t.Optional[int] = None,
        *,
        metric: t.Union[None, str, AustinStatsType] = None,
        per_thread: bool = False,
        lines: bool = False,
    ) -> StacksResult:
        """Get the ``n`` heaviest distinct stacks.

        Stacks are merged across processes and threads unless ``per_thread``
        is true. Frames are functions, or lines if ``lines`` is true.
        """
        stats = self.stats(metric)
        profile_total, profile_samples = self._totals(stats)

        Key = t.Tuple[
            t.Optional[ProcessId], t.Optional[ThreadName], t.Tuple[Location, ...]
        ]
        values: t.Counter[Key] = Counter()
        samples: t.Counter[Key] = Counter()

        for pid, thread in self._threads(stats):
            where = (pid, thread.label.thread) if per_thread else (None, None)

            if thread.own:
                values[(*where, ())] += thread.own
                samples[(*where, ())] += _own_samples(thread)

            path: t.List[Location] = []
            for node, entering in _walk(thread.children.values()):
                if not entering:
                    path.pop()
                    continue
                path.append(Location.from_frame(node.label, lines))
                if node.own:
                    key = (*where, tuple(path))
                    values[key] += node.own
                    samples[key] += _own_samples(node)

        ranked = sorted(values, key=lambda k: values[k], reverse=True)
        return StacksResult(
            paths=self.paths,
            metric=stats.stats_type,
            profile_total=profile_total,
            profile_samples=profile_samples,
            entries=tuple(
                Stack(
                    frames=key[2],
                    value=values[key],
                    samples=samples[key],
                    pct=_pct(values[key], profile_total),
                    pid=key[0],
                    thread=key[1],
                )
                for key in ranked[:n]
            ),
            count=len(ranked),
        )

    def _neighbours(
        self,
        kind: str,
        selector: Selector,
        metric: t.Union[None, str, AustinStatsType],
        lines: bool,
    ) -> Neighbours:
        stats = self.stats(metric)
        profile_total, profile_samples = self._totals(stats)
        match = matcher(selector)

        matched: t.Set[Location] = set()
        own = own_samples = total = total_samples = 0
        values: t.Counter[Location] = Counter()
        samples: t.Counter[Location] = Counter()

        # Each path entry is (location, is a match, counted edge). Edges are
        # counted once per stack, so that recursion does not inflate them.
        path: t.List[t.Tuple[Location, bool, t.Optional[Location]]] = []
        counted: t.Counter[Location] = Counter()
        depth = 0  # Number of matching frames in the current path

        for node, entering in _walk(self._roots(stats)):
            if not entering:
                _, is_match, edge = path.pop()
                depth -= is_match
                if edge is not None:
                    counted[edge] -= 1
                continue

            frame = node.label
            key = Location.from_frame(frame, lines)
            is_match = match(frame)

            edge = None
            if kind == "callers" and is_match:
                edge = path[-1][0] if path else ROOT
            elif kind == "callees" and path and path[-1][1]:
                edge = key
            if edge is not None:
                if not counted[edge]:
                    values[edge] += node.total
                    samples[edge] += node.samples
                counted[edge] += 1

            if is_match:
                matched.add(Location.from_frame(frame, lines))
                own += node.own
                own_samples += _own_samples(node)
                if not depth:
                    total += node.total
                    total_samples += node.samples

            depth += is_match
            path.append((key, is_match, edge))

        if not matched:
            raise self._no_match(selector)

        if kind == "callees" and own:
            values[SELF] += own
            samples[SELF] += own_samples

        return Neighbours(
            paths=self.paths,
            metric=stats.stats_type,
            profile_total=profile_total,
            profile_samples=profile_samples,
            kind=kind,
            matched=tuple(sorted(matched, key=str)),
            own=own,
            total=total,
            samples=total_samples,
            entries=tuple(
                Edge(
                    location=key,
                    value=values[key],
                    samples=samples[key],
                    pct=_pct(values[key], profile_total),
                    share=_pct(values[key], total),
                )
                for key in sorted(values, key=lambda k: values[k], reverse=True)
            ),
        )

    def callers(
        self,
        selector: Selector,
        *,
        metric: t.Union[None, str, AustinStatsType] = None,
        lines: bool = False,
    ) -> Neighbours:
        """Get the callers of the matched frames, heaviest first.

        The value of a caller is the total of the matched frames when called by
        it.
        """
        return self._neighbours("callers", selector, metric, lines)

    def callees(
        self,
        selector: Selector,
        *,
        metric: t.Union[None, str, AustinStatsType] = None,
        lines: bool = False,
    ) -> Neighbours:
        """Get the callees of the matched frames, heaviest first.

        The value of a callee is its total when called by the matched frames.
        """
        return self._neighbours("callees", selector, metric, lines)

    def tree(
        self,
        root: t.Optional[Selector] = None,
        *,
        metric: t.Union[None, str, AustinStatsType] = None,
        max_depth: t.Optional[int] = None,
        min_pct: float = 1.0,
        lines: bool = False,
    ) -> CallTree:
        """Get the call tree of the profile, merged across threads.

        If ``root`` is given, the tree is rooted at the matched frames instead,
        merging the subtrees of their outermost occurrences in each stack.
        Nodes whose total is below ``min_pct`` percent of the profile total, or
        that are deeper than ``max_depth``, are pruned.
        """
        stats = self.stats(metric)
        profile_total, profile_samples = self._totals(stats)

        @dataclass
        class Acc:
            own: int = 0
            total: int = 0
            samples: int = 0
            children: t.Dict[Location, "Acc"] = field(default_factory=dict)

        top = Acc()

        def merge(src: FrameStats, dst: Acc) -> None:
            stack = [(src, dst)]
            while stack:
                s, d = stack.pop()
                d.own += s.own
                d.total += s.total
                d.samples += s.samples
                for child in s.children.values():
                    key = Location.from_frame(child.label, lines)
                    stack.append((child, d.children.setdefault(key, Acc())))

        matched: t.Set[Location] = set()
        if root is None:
            label = ALL
            for _, thread in self._threads(stats):
                top.own += thread.own
                top.total += thread.total
                top.samples += thread.samples
                for child in thread.children.values():
                    key = Location.from_frame(child.label, lines)
                    merge(child, top.children.setdefault(key, Acc()))
        else:
            match = matcher(root)
            depth = 0
            for node, entering in _walk(self._roots(stats)):
                if not match(node.label):
                    continue
                if not entering:
                    depth -= 1
                    continue
                matched.add(Location.from_frame(node.label, lines))
                if not depth:
                    merge(node, top)
                depth += 1
            if not matched:
                raise self._no_match(root)
            label = (
                next(iter(matched))
                if len(matched) == 1
                else Location("", f"<{len(matched)} locations>")
            )

        def make(location: Location, acc: Acc) -> CallNode:
            return CallNode(
                location=location,
                own=acc.own,
                total=acc.total,
                samples=acc.samples,
                pct=_pct(acc.total, profile_total),
            )

        tree = make(label, top)
        pending = [(tree, top, 0)]
        while pending:
            call_node, acc, level = pending.pop()
            if max_depth is not None and level >= max_depth:
                continue
            for key, child_acc in sorted(
                acc.children.items(), key=lambda kv: kv[1].total, reverse=True
            ):
                if _pct(child_acc.total, profile_total) < min_pct:
                    continue
                child_node = make(key, child_acc)
                call_node.children.append(child_node)
                pending.append((child_node, child_acc, level + 1))

        return CallTree(
            paths=self.paths,
            metric=stats.stats_type,
            profile_total=profile_total,
            profile_samples=profile_samples,
            root=tree,
            matched=tuple(sorted(matched, key=str)),
        )

    def tasks(
        self, *, metric: t.Union[None, str, AustinStatsType] = None
    ) -> TasksResult:
        """Get the asyncio task trees of the profile (Python 3.14+ only).

        A task is a child of the task that awaits it. Root tasks are grouped by
        the thread that owns them, and sorted by total within each thread, as
        are the children of each task. See :class:`TaskNode` for the meaning
        of the values.
        """
        stats = self.stats(metric)
        stats_type = stats.stats_type
        profile_total, profile_samples = self._totals(stats)
        wall = stats_type is AustinStatsType.WALL

        names: t.Dict[int, t.Optional[str]] = {}
        owners: t.Dict[int, t.Tuple[ProcessId, ThreadName]] = {}
        waiters: t.Dict[int, int] = {}
        running: t.Counter[int] = Counter()
        awaiting: t.Counter[int] = Counter()

        for sample in self.samples:
            value = sample_metric(sample, stats_type) or 0
            for task in _iter_tasks(sample.tasks):
                task_id = task.task_id
                if task.name is not None or task_id not in names:
                    names[task_id] = task.name
                owners[task_id] = (sample.pid, sample.thread)
                for child in task.awaiting:
                    waiters[child.task_id] = task_id
                if not value:
                    continue
                if task_id == sample.running_task:
                    running[task_id] += value
                elif wall:
                    awaiting[task_id] += value

        children: t.Dict[int, t.List[int]] = defaultdict(list)
        for task_id, waiter in waiters.items():
            if task_id in owners and waiter in owners:
                children[waiter].append(task_id)

        nodes = {
            task_id: TaskNode(
                task_id=task_id,
                name=names[task_id],
                pid=pid,
                thread=thread,
                running=running[task_id],
                awaiting=awaiting[task_id],
                total=running[task_id] + awaiting[task_id],
                pct=0.0,
            )
            for task_id, (pid, thread) in owners.items()
        }

        # Build the trees from the root tasks down. A task in a waiter cycle,
        # which only garbled data can produce, becomes a root of its own.
        roots: t.List[TaskNode] = []
        seen: t.Set[int] = set()
        candidates = [_ for _ in nodes if waiters.get(_) not in nodes]
        candidates.extend(_ for _ in nodes if _ not in candidates)
        order: t.List[TaskNode] = []  # Parents before children
        for root_id in candidates:
            if root_id in seen:
                continue
            seen.add(root_id)
            roots.append(nodes[root_id])
            stack = [root_id]
            while stack:
                task_id = stack.pop()
                order.append(nodes[task_id])
                for child_id in children[task_id]:
                    if child_id not in seen:
                        seen.add(child_id)
                        nodes[task_id].children.append(nodes[child_id])
                        stack.append(child_id)

        for node in reversed(order):
            if not wall:
                node.total += sum(c.total for c in node.children)
            node.pct = _pct(node.total, profile_total)
            node.children.sort(key=lambda c: c.total, reverse=True)

        threads: t.Dict[t.Tuple[ProcessId, ThreadName], t.List[TaskNode]] = {}
        for root in roots:
            threads.setdefault((root.pid, root.thread), []).append(root)

        return TasksResult(
            paths=self.paths,
            metric=stats_type,
            profile_total=profile_total,
            profile_samples=profile_samples,
            roots=tuple(
                root
                for group in threads.values()
                for root in sorted(group, key=lambda r: r.total, reverse=True)
            ),
        )

    def task_stacks(
        self,
        task: t.Optional[TaskSelector] = None,
        n: t.Optional[int] = None,
        *,
        metric: t.Union[None, str, AustinStatsType] = None,
        lines: bool = False,
    ) -> TaskStacksResult:
        """Get the ``n`` heaviest positions of asyncio tasks (Python 3.14+).

        A task's position is its coroutine chain while suspended, or the frames
        it was running. Each position gets the value of the samples in which a
        task was running there and, in wall time, the time a task was
        suspended there. Positions are merged across the tasks that match the
        ``task`` selector (see :func:`task_matcher`), or across all tasks if
        not given. Frames are functions, or lines if ``lines`` is true.
        """
        stats = self.stats(metric)
        stats_type = stats.stats_type
        profile_total, profile_samples = self._totals(stats)
        wall = stats_type is AustinStatsType.WALL
        match = self._match_tasks(task) if task is not None else None

        matched: t.Dict[int, t.Optional[str]] = {}

        # Accumulate by position first, and only convert the distinct ones to
        # locations at the end. Samples share the position tuples of tasks
        # that have not moved, so their identity is a cheap key.
        positions: t.Dict[int, t.Tuple[AustinFrame, ...]] = {}
        raw: t.Dict[int, t.List[int]] = {}  # [running, awaiting, samples]
        for sample in self.samples:
            value = sample_metric(sample, stats_type) or 0
            for node in _iter_tasks(sample.tasks):
                if match is not None and not match(node):
                    continue
                if node.name is not None or node.task_id not in matched:
                    matched[node.task_id] = node.name
                is_running = node.task_id == sample.running_task
                if not value or not (is_running or wall):
                    continue
                position = id(node.frames)
                try:
                    acc = raw[position]
                except KeyError:
                    positions[position] = node.frames
                    acc = raw[position] = [0, 0, 0]
                acc[0 if is_running else 1] += value
                acc[2] += 1

        Key = t.Tuple[Location, ...]
        running: t.Counter[Key] = Counter()
        awaiting: t.Counter[Key] = Counter()
        samples: t.Counter[Key] = Counter()
        for position, (run, wait, count) in raw.items():
            key = tuple(Location.from_frame(f, lines) for f in positions[position])
            running[key] += run
            awaiting[key] += wait
            samples[key] += count

        values = running + awaiting
        ranked = sorted(values, key=lambda k: values[k], reverse=True)
        return TaskStacksResult(
            paths=self.paths,
            metric=stats_type,
            profile_total=profile_total,
            profile_samples=profile_samples,
            entries=tuple(
                TaskStack(
                    frames=key,
                    value=values[key],
                    running=running[key],
                    awaiting=awaiting[key],
                    samples=samples[key],
                    pct=_pct(values[key], profile_total),
                )
                for key in ranked[:n]
            ),
            count=len(ranked),
            matched=tuple(
                f"{name if name is not None else '<unnamed>'} #{task_id}"
                for task_id, name in sorted(matched.items())
            ),
        )
