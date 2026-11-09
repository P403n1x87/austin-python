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

    ``frames`` is this task's last-known position: its coroutine chain if it
    was suspended, or the frames it was running if it was running.
    ``awaiting`` are the tasks this task is itself awaiting, i.e. the tasks
    for which this task is the direct waiter.

    This is the structure of the tree only. The time tasks spend at their
    positions is carried by AustinTaskReport (see AustinSample.task_reports)
    and, while they are running, by the samples they are running at (see
    AustinSample.running_task).
    """

    task_id: int
    name: t.Optional[str]
    frames: t.Tuple[AustinFrame, ...] = ()
    awaiting: t.Tuple["AustinTask", ...] = ()


@dataclass(frozen=True)
class AustinTaskReport:
    """A report of a task's position (3.14+ only).

    Austin only reports a task's position when it has changed. ``frames`` is
    the task's new position, and ``elapsed`` is how long the task was
    *suspended* at its ``previous`` one, which this report replaces -- the
    earliest point at which that duration could be known at all. Austin
    doesn't report it: readers work it out as the time of the task's thread's
    samples while the task held that position without running. It is await
    time only: the time a task spends running is the time of the samples it
    is running at (see AustinSample.running_task). Always 0 in CPU mode, where
    a suspended task uses no CPU.

    ``previous`` is None on a task's first report, which has no previous
    position (and so ``elapsed`` is 0). A report with no ``frames`` closes the
    task: it is gone, and ``elapsed`` is the time at its last position. At the
    end of a stream, each task still alive gets a report with ``frames`` equal
    to ``previous``, carrying the time it has spent at its position since.

    Each report is attached to exactly one sample, so summing ``elapsed``
    over every sample's reports counts each duration once.
    """

    task_id: int
    name: t.Optional[str]
    frames: t.Tuple[AustinFrame, ...]
    previous: t.Optional[t.Tuple[AustinFrame, ...]]
    elapsed: MicroSeconds

    @property
    def closing(self) -> bool:
        """Whether this report closes the task."""
        return not self.frames


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
    # The live tasks owned by this sample's thread, as of this sample.
    tasks: t.Tuple[AustinTask, ...] = ()
    # The task reports that came with this sample, each one exactly once.
    task_reports: t.Tuple[AustinTaskReport, ...] = ()
    # The task this sample's thread was running, if any. The sample's metrics
    # then belong to that task too, at its latest position (see AustinTask).
    running_task: t.Optional[int] = None

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
