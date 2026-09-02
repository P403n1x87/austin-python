import typing as t
from dataclasses import dataclass

ProcessId = int
ThreadName = str
InterpreterId = int
MicroSeconds = int
Bytes = int


@dataclass(frozen=True)
class AustinFrame:
    """Python frame."""

    filename: str
    function: str
    line: int
    line_end: t.Optional[int] = None
    column: t.Optional[int] = None
    column_end: t.Optional[int] = None


@dataclass(frozen=True)
class AustinMetrics:
    """Austin metric."""

    time: t.Optional[MicroSeconds] = None
    memory: t.Optional[Bytes] = None


@dataclass(frozen=True)
class AustinEvent:
    """Base class for Austin events."""

    pass


@dataclass(frozen=True)
class AustinMetadata(AustinEvent):
    """Austin metadata."""

    name: str
    value: str


@dataclass(frozen=True)
class AustinTask:
    """A node in an asyncio task tree (3.14+ only).

    ``frames`` is this task's own last-known suspended coroutine-chain
    snapshot -- empty if it was never captured suspended (e.g. it was only
    ever seen actively running rather than awaiting something). ``awaiting``
    are the tasks this task is itself awaiting, i.e. the tasks for which this
    task is the direct waiter.

    ``elapsed`` does NOT describe ``frames``. Austin only re-samples a task's
    chain (and reports a new node) when its identity has actually changed
    since the last scan, so the two are always one step apart: ``frames`` is
    the task's brand new position (just captured because it changed), while
    ``elapsed`` is how long the task dwelled at its *previous*, now-replaced
    position -- the earliest point at which that duration could be known at
    all. None on a task's first-ever sighting, when there is no previous
    position to report a duration for. Always a wall/CPU time value, or None
    if Austin was run in pure memory mode (no per-task memory delta exists to
    report -- see austin's own py_proc.c, _py_proc__maybe_discover_asyncio).
    """

    task_id: int
    name: t.Optional[str]
    frames: t.Tuple[AustinFrame, ...] = ()
    elapsed: t.Optional[MicroSeconds] = None
    awaiting: t.Tuple["AustinTask", ...] = ()


@dataclass(frozen=True)
class AustinSample(AustinEvent):
    """Austin sample."""

    Key = t.Tuple[
        ProcessId,
        t.Optional[InterpreterId],
        ThreadName,
        t.Optional[t.Tuple[AustinFrame, ...]],
        t.Optional[bool],
        t.Optional[bool],
    ]

    pid: ProcessId
    iid: t.Optional[InterpreterId]
    thread: ThreadName
    metrics: AustinMetrics
    frames: t.Optional[t.Tuple[AustinFrame, ...]] = None
    gc: t.Optional[bool] = None
    idle: t.Optional[bool] = None
    tasks: t.Tuple[AustinTask, ...] = ()

    def key(
        self,
    ) -> "AustinSample.Key":
        """Return a key for this sample."""
        return (
            self.pid,
            self.iid,
            self.thread,
            self.frames,
            self.gc,
            self.idle,
        )

    @classmethod
    def from_key_and_metrics(
        cls, key: "AustinSample.Key", metrics: AustinMetrics
    ) -> "AustinSample":
        """Create a sample from a key."""
        return cls(
            pid=key[0],
            iid=key[1],
            thread=key[2],
            frames=key[3],
            gc=key[4],
            idle=key[5],
            metrics=metrics,
        )


class AustinEventIterator:
    """Base class for Austin event iterators."""

    def __iter__(self) -> t.Iterator[AustinEvent]:
        """Return an iterator over Austin events."""
        raise NotImplementedError("Subclasses must implement __iter__ method.")
