import typing as t
from collections import namedtuple
from dataclasses import dataclass


ThreadName = namedtuple("ThreadName", ["thread", "iid"])
ProcessId = int
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
