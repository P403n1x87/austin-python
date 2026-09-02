import abc
import asyncio
import typing as t
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from enum import Enum

from austin.events import AustinEvent
from austin.events import AustinEventIterator
from austin.events import AustinFrame
from austin.events import AustinMetadata
from austin.events import AustinMetrics
from austin.events import AustinSample
from austin.events import AustinTask
from austin.events import InterpreterId
from austin.events import ProcessId
from austin.events import ThreadName

# Guards against a corrupted/cyclic waiter graph in the source stream -- a
# real await chain never comes anywhere close to this. Mirrors austin's own
# WHERE_MAX_TREE_DEPTH (src/events.c).
MAX_TASK_TREE_DEPTH = 64


def to_varint(n: int) -> bytes:
    """Convert an integer to a variable-length integer."""
    result = bytearray()
    b = 0

    if n < 0:
        b |= 0x40
        n = -n

    b |= n & 0x3F

    n >>= 6
    if n:
        b |= 0x80

    result.append(b)

    while n:
        b = n & 0x7F
        n >>= 7
        if n:
            b |= 0x80
        result.append(b)

    return bytes(result)


class MojoParseError(Exception):
    """MOJO parse error."""

    pass


class MojoEvents:
    """MOJO events."""

    RESERVED = 0
    METADATA = 1
    STACK = 2
    FRAME = 3
    FRAME_INVALID = 4
    FRAME_REF = 5
    FRAME_KERNEL = 6
    GC = 7
    IDLE = 8
    METRIC_TIME = 9
    METRIC_MEMORY = 10
    STRING = 11
    STRING_REF = 12
    STACK_REPEAT = 13
    TASK_STACK = 14
    TASK_WAITER = 15


class MojoEventHandler:
    """MOJO event handler."""

    __event__ = 0

    def __call__(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Handle the event."""
        ...


@dataclass(frozen=True, eq=True)
class MojoEvent:
    """MOJO event."""

    EVENT_ID: t.ClassVar = None
    raw: t.ClassVar[bytes] = b""

    def ref(self) -> int:
        return getattr(self, fields(self)[0].name)

    def to_bytes(self) -> bytes:
        buffer = bytearray([self.EVENT_ID])
        for f in fields(self):
            value = getattr(self, f.name)
            field_type = (
                t.get_args(f.type)[0] if t.get_origin(f.type) is t.Union else f.type
            )
            if field_type is str:
                buffer += value.encode()
                buffer += b"\x00"
            elif field_type is int:
                buffer += to_varint(value)
            elif issubclass(field_type, MojoEvent):
                buffer += to_varint(value.ref())
            else:
                msg = f"Invalid MOJO event field type {f.type}"
                raise TypeError(msg)
        return bytes(buffer)


class MojoMetricType(str, Enum):
    """MOJO metric types."""

    TIME = "time"
    MEMORY = "memory"


@dataclass(frozen=True, eq=True)
class MojoMetric(MojoEvent):
    """MOJO metric."""

    metric_type: MojoMetricType
    value: int

    def to_bytes(self) -> bytes:
        buffer = bytearray(
            [
                (
                    MojoEvents.METRIC_TIME
                    if self.metric_type is MojoMetricType.TIME
                    else MojoEvents.METRIC_MEMORY
                )
            ]
        )
        buffer += to_varint(self.value)
        return bytes(buffer)


@dataclass(frozen=True, eq=True)
class MojoString(MojoEvent):
    """MOJO string."""

    EVENT_ID = MojoEvents.STRING

    key: int
    value: str


@dataclass(frozen=True, eq=True)
class MojoStringReference(MojoEvent):
    """MOJO string reference."""

    EVENT_ID = MojoEvents.STRING_REF

    string: MojoString


class MojoIdle(MojoEvent):
    """MOJO idle event."""

    EVENT_ID = MojoEvents.IDLE

    pass


@dataclass(frozen=True, eq=True)
class MojoMetadata(MojoEvent):
    """MOJO metadata."""

    EVENT_ID = MojoEvents.METADATA

    key: str
    value: str


@dataclass(frozen=True, eq=True)
class MojoStack(MojoEvent):
    """MOJO stack."""

    EVENT_ID = MojoEvents.STACK

    pid: int
    iid: int
    tid: str


@dataclass(frozen=True, eq=True)
class MojoStackRepeat(MojoEvent):
    """MOJO stack repeat event.

    Signals that the previous sample for this thread provides the base
    (outermost) frames for the current sample.  The frames accumulated so
    far in the current sample are the innermost (top) part of the call stack.
    """

    EVENT_ID = MojoEvents.STACK_REPEAT


@dataclass(frozen=True, eq=True)
class MojoTaskWaiter(MojoEvent):
    """MOJO task waiter event.

    One edge of a task's waiter DAG: ``task_id`` is awaited by
    ``waiter_id``.
    """

    EVENT_ID = MojoEvents.TASK_WAITER

    task_id: int
    waiter_id: int


@dataclass(frozen=True, eq=True)
class MojoTaskStack(MojoEvent):
    """MOJO task stack event.

    Introduces the coroutine stack of a suspended task, keyed by the remote
    address of its TaskObj and its (possibly cached) name key (0 if
    unresolved). The frames that make up the stack, and the trailing time
    metric that terminates it, follow as ordinary MOJO_FRAME/MOJO_FRAME_REF/
    MOJO_METRIC_TIME events rather than being part of this event itself --
    see BaseMojoStreamReader's task-stack handling.

    The trailing metric is always a time value, and describes how long the
    task dwelled at its PREVIOUS position, not the frames that just followed
    this event -- see AustinTask's own docstring for why the two are always
    one step apart. It never appears at all when austin was run in pure
    memory mode.
    """

    EVENT_ID = MojoEvents.TASK_STACK

    task_id: int
    name_key: int


@dataclass(frozen=True, eq=True)
class MojoFrame(MojoEvent):
    """MOJO frame."""

    EVENT_ID = MojoEvents.FRAME

    key: int
    filename: MojoString
    scope: MojoString
    line: int
    line_end: t.Optional[int] = None
    column: t.Optional[int] = None
    column_end: t.Optional[int] = None


@dataclass(frozen=True, eq=True)
class MojoKernelFrame(MojoEvent):
    """MOJO kernel frame."""

    EVENT_ID = MojoEvents.FRAME_KERNEL

    scope: str


@dataclass(frozen=True, eq=True)
class MojoSpecialFrame(MojoEvent):
    """MOJO special frame."""

    EVENT_ID = MojoEvents.FRAME_INVALID

    label: str


@dataclass(frozen=True, eq=True)
class MojoFrameReference(MojoEvent):
    """MOJO frame reference."""

    EVENT_ID = MojoEvents.FRAME_REF

    frame: MojoFrame


EMPTY = MojoString(0, "")
UNKNOWN = MojoString(1, "<unknown>")


def handles(
    e: int,
) -> t.Callable[[t.Callable], MojoEventHandler]:
    """MOJO handler registration decorator."""

    def _(f: t.Callable) -> MojoEventHandler:
        (h := t.cast(MojoEventHandler, f)).__event__ = e
        return h

    return _


@dataclass
class _RunningSample:
    pid: ProcessId
    thread: ThreadName
    iid: t.Optional[InterpreterId] = None
    frames: t.List[MojoFrame] = field(default_factory=list)
    metrics: t.Dict[MojoMetricType, MojoMetric] = field(default_factory=dict)
    gc: t.Optional[bool] = None
    idle: t.Optional[bool] = None


@dataclass
class _RunningTaskStack:
    task_id: int
    name_key: int
    frames: t.List[MojoFrame] = field(default_factory=list)


@dataclass
class _TaskInfo:
    """Best-known state for one task_id.

    Built up from MOJO_TASK_STACK events as they arrive. ``owner`` is the
    (pid, thread) of whichever sample's wire bracket this task's most recent
    MOJO_TASK_STACK fell within -- see BaseMojoStreamReader's task-stack
    handling for why that bracket is the only ownership signal that exists.
    """

    name: t.Optional[str]
    owner: t.Tuple[ProcessId, ThreadName]
    frames: t.Tuple[AustinFrame, ...] = ()
    elapsed: t.Optional[int] = None


def int_reader() -> t.Generator[t.Optional[int], bytes, int]:
    (b,) = yield None
    while True:
        n = 0
        s = 6
        n |= b & 0x3F
        sign = b & 0x40
        while b & 0x80:
            (b,) = yield None
            n |= (b & 0x7F) << s
            s += 7
        (b,) = yield -n if sign else n


def str_reader() -> t.Generator[t.Optional[str], bytes, str]:
    """Read a string from the MOJO file."""
    buffer = bytearray(1024)
    i = 0
    (b,) = yield None
    while True:
        if b == 0:
            (b,) = yield bytes(buffer[:i]).decode(errors="replace")
            i = 0
        else:
            try:
                buffer[i] = b
            except IndexError:
                # Expand the buffer if needed
                buffer += bytearray(i - len(buffer) + 1)
                buffer[i] = b
            (b,) = yield None
            i += 1


class BaseMojoStreamReader(AustinEventIterator):
    """Base MOJO stream reader.

    Converts a stream of MOJO events into Austin events, that is samples and
    metadata.
    """

    __handlers__: t.Optional[t.Dict[int, t.Callable[[], None]]] = None

    def __init__(self, mojo: t.Any) -> None:
        if self.__handlers__ is None:
            self.__class__.__handlers__ = {
                f.__event__: f
                for f in self.__class__.__dict__.values()
                if hasattr(f, "__event__")
            }

        self.mojo = mojo
        self.mojo_version: t.Optional[int] = None

        # Reference maps
        self._frame_map: t.Dict[t.Tuple[int, int], MojoFrame] = {}
        self._string_map: t.Dict[t.Tuple[int, int], MojoString] = {}

        # Internal parsing state
        self._offset = 0
        self._last_read = 0
        self._last_bytes = bytearray()
        self._running_sample: t.Optional[_RunningSample] = None

        self._int_reader = int_reader()
        next(self._int_reader)
        self._str_reader = str_reader()
        next(self._str_reader)

        # Per-thread previous frame list for STACK_REPEAT expansion.
        # Key: (pid, thread_name); value: list of MojoFrame accumulated by the
        # last fully-finalised sample for that thread.
        self._prev_frames: t.Dict[t.Tuple[int, str], t.List[MojoFrame]] = {}

        # Suspended-task coroutine-chain state (3.14+ asyncio). A task stack's
        # frames/terminating time metric are ordinary MOJO_FRAME/MOJO_FRAME_REF/
        # MOJO_METRIC_TIME events on the wire, indistinguishable by event ID
        # alone from those of the enclosing regular stack sample -- so while
        # this is not None, get_frame_ref/get_time_metric route to it instead
        # of the running sample.
        self._running_task_stack: t.Optional[_RunningTaskStack] = None

        # Best-known state per task_id, keyed by remote TaskObj address.
        self._task_info: t.Dict[int, _TaskInfo] = {}

        # Best-known waiter DAG edges: (task_id, waiter_id) pairs, meaning
        # task_id is awaited by waiter_id. The wire re-emits a task's
        # *complete* current waiter set whenever it changes (never a diff --
        # see py_asyncio.c's fingerprint comment), so a fresh batch for a
        # task_id replaces its previous edges; batch boundaries are inferred
        # from consecutive same-task_id events (see get_task_waiter).
        self._task_edges: t.Set[t.Tuple[int, int]] = set()
        self._last_waiter_task_id: t.Optional[int] = None

        # Austin events
        self.metadata: t.Dict[str, str] = {}
        self.samples: t.List[AustinSample] = []

    def ref(self, n: int) -> t.Tuple[int, int]:
        """Return a per-process reference key.

        MOJO objects that carry a numeric reference is to be interpreted as
        relative to the current process, so it has to be combined with the
        last seen PID.
        """
        assert self._running_sample is not None
        return (self._running_sample.pid, n)

    def _read(self, data: bytes, n: int = 1) -> bytes:
        """Read bytes from the MOJO file."""
        if len(data) != n:
            raise ValueError(
                f"Expected {n} bytes, got {len(data)} at offset {self._offset}"
            )

        self._offset += self._last_read
        self._last_read = n

        self._last_bytes.extend(data)

        return data

    def get_metadata(self, name: str, value: str) -> MojoMetadata:
        """Parse metadata."""
        metadata = MojoMetadata(name, value)

        self.metadata[metadata.key] = metadata.value

        return metadata

    @property
    def mode(self) -> t.Optional[str]:
        return self.metadata.get("mode")

    @property
    def gc(self) -> t.Optional[str]:
        return self.metadata.get("gc")

    def _finalize_sample(self) -> AustinSample:
        """Finalize the current sample."""
        assert self._running_sample is not None, self._running_sample

        self.samples.append(
            sample := AustinSample(
                pid=self._running_sample.pid,
                iid=self._running_sample.iid,
                thread=self._running_sample.thread,
                metrics=AustinMetrics(
                    **{
                        metric_type.value: metric.value
                        for metric_type, metric in self._running_sample.metrics.items()
                    }
                ),
                frames=(
                    tuple(
                        AustinFrame(
                            filename=mf.filename.value,
                            function=mf.scope.value,
                            line=mf.line,
                            line_end=mf.line_end,
                            column=mf.column,
                            column_end=mf.column_end,
                        )
                        for mf in self._running_sample.frames
                    )
                    if self._running_sample.frames
                    else None
                ),
                gc=self._running_sample.gc,
                idle=self._running_sample.idle,
                tasks=self.get_tasks(
                    self._running_sample.pid, self._running_sample.thread
                ),
            )
        )

        # Save fully-expanded frame list for future STACK_REPEAT events from
        # this thread.
        self._prev_frames[(self._running_sample.pid, self._running_sample.thread)] = (
            list(self._running_sample.frames)
        )

        self._running_sample = None

        return sample

    @staticmethod
    def _is_native_frame(frame: MojoFrame) -> bool:
        name = frame.filename.value
        return not name.endswith(".py") and not (
            name.startswith("<") and name.endswith(">")
        )

    def get_stack_repeat(self) -> MojoStackRepeat:
        """Handle a STACK_REPEAT event.

        The previous sample's frames (minus any trailing native frames that
        belonged to the old top-of-stack above the eval frame) are prepended
        to the frames accumulated so far.
        """
        assert self._running_sample is not None
        key = (self._running_sample.pid, self._running_sample.thread)
        prev = list(self._prev_frames.get(key, []))
        # Strip native frames from the innermost (top) end of the previous
        # stack — those were above the eval frame and have now been replaced
        # by the new frames in the current sample.
        while prev and self._is_native_frame(prev[-1]):
            prev.pop()
        self._running_sample.frames = prev + self._running_sample.frames
        return MojoStackRepeat()

    def get_stack(self, pid: int, iid: t.Optional[int], thread: str) -> MojoStack:
        """Parse a stack."""
        if self._running_sample is not None:
            self._finalize_sample()

        self._running_sample = _RunningSample(
            pid=pid,
            iid=iid,
            thread=thread,
            idle=False if self.mode == "full" else None,
            gc=False if self.gc is not None else None,
        )

        return MojoStack(pid, iid if iid is not None else -1, thread)

    def _lookup_string(self, index: int) -> MojoString:
        return UNKNOWN if index == 1 else self._string_map[self.ref(index)]

    def get_frame(
        self,
        key: int,
        filename_index: int,
        scope_index: int,
        line: int,
        line_end: t.Optional[int],
        column: t.Optional[int],
        column_end: t.Optional[int],
    ) -> MojoFrame:
        """Parse a frame."""
        filename = self._lookup_string(filename_index)
        scope = self._lookup_string(scope_index)

        if self.mojo_version == 1:
            assert line_end == column == column_end is None

        self._frame_map[self.ref(key)] = (
            frame := MojoFrame(key, filename, scope, line, line_end, column, column_end)
        )

        return frame

    def get_frame_ref(self, ref: int) -> MojoFrameReference:
        """Parse a frame reference."""
        frame = self._frame_map[self.ref(ref)]

        if self._running_task_stack is not None:
            self._running_task_stack.frames.append(frame)
        else:
            assert self._running_sample is not None, self._running_sample
            self._running_sample.frames.append(frame)

        return MojoFrameReference(frame)

    def get_task_waiter(self, task_id: int, waiter_id: int) -> MojoTaskWaiter:
        """Parse a task waiter edge."""
        if self._last_waiter_task_id != task_id:
            # Starting a fresh batch for this task_id: the wire re-emits the
            # complete current waiter set whenever it changes, so drop
            # whatever we knew about this task_id's waiters before.
            self._task_edges = {e for e in self._task_edges if e[0] != task_id}
            self._last_waiter_task_id = task_id

        self._task_edges.add((task_id, waiter_id))

        return MojoTaskWaiter(task_id, waiter_id)

    def get_task_stack(self, task_id: int, name_key: int) -> MojoTaskStack:
        """Parse the header of a suspended task's coroutine-chain snapshot.

        The frames and terminating time metric that complete it arrive as
        subsequent, ordinary events -- see get_frame_ref/get_time_metric.
        """
        self._running_task_stack = _RunningTaskStack(task_id, name_key)

        return MojoTaskStack(task_id, name_key)

    def _finalize_task_stack(self, elapsed: int) -> None:
        """Finalize the running task stack.

        Triggered by its terminating MOJO_METRIC_TIME (see get_time_metric).
        ``ts.frames`` (the task's brand new position) and ``elapsed`` (how
        long it dwelled at its previous one) describe two different moments
        even though they land in the same _TaskInfo/AustinTask -- see
        AustinTask's own docstring. The task's owner is recorded as whichever
        sample is currently being assembled: this event only ever arrives
        bracketed inside that sample's own MOJO_STACK...next-MOJO_STACK
        window, so there's nothing else it could belong to.

        An empty ``ts.frames`` is a closing flush -- the task has just been
        evicted (completed, or otherwise gone), and this only carries its
        final dwell time, with no new content and no meaningful owner (by
        the time eviction runs, every thread for this cycle has already had
        its turn, so "whichever sample is currently being assembled" is
        arbitrary here, not this task's actual owner). Only update elapsed
        on whatever's already known; leave frames/owner untouched rather
        than wiping the task's last real position right as it disappears.
        """
        ts = self._running_task_stack
        assert ts is not None, ts
        assert self._running_sample is not None, self._running_sample

        if not ts.frames:
            existing = self._task_info.get(ts.task_id)
            if existing is not None:
                existing.elapsed = elapsed
            self._running_task_stack = None
            return

        name = self._lookup_string(ts.name_key).value if ts.name_key else None

        self._task_info[ts.task_id] = _TaskInfo(
            name=name,
            owner=(self._running_sample.pid, self._running_sample.thread),
            frames=tuple(
                AustinFrame(
                    filename=mf.filename.value,
                    function=mf.scope.value,
                    line=mf.line,
                    line_end=mf.line_end,
                    column=mf.column,
                    column_end=mf.column_end,
                )
                for mf in ts.frames
            ),
            elapsed=elapsed,
        )

        self._running_task_stack = None

    def get_tasks(self, pid: ProcessId, thread: ThreadName) -> t.Tuple[AustinTask, ...]:
        """Return the current best-known root tasks owned by (pid, thread).

        Every root task it owns (nobody awaits it), and everything it
        transitively awaits, as one AustinTask per root -- a thread can own
        more than one at once (e.g. several siblings under one gather()).

        Mirrors austin's own where_event_handler__render_tree: a task only
        appears if it was itself captured suspended at least once (a waiter
        edge naming a task we never saw a MOJO_TASK_STACK for -- e.g. it was
        only ever seen actively running -- is omitted, exactly like austin's
        own where_event_handler__find_task returning NULL for it). Like that
        C-side counterpart, this is a no-op (returns empty) when (pid,
        thread) owns no tasks, so callers can call it unconditionally.
        """

        def has_parent(task_id: int) -> bool:
            return any(t_id == task_id for t_id, _ in self._task_edges)

        def build(task_id: int, depth: int) -> AustinTask:
            info = self._task_info[task_id]
            awaiting = (
                tuple(
                    build(awaited_id, depth + 1)
                    for awaited_id, waiter_id in self._task_edges
                    if waiter_id == task_id and awaited_id in self._task_info
                )
                if depth < MAX_TASK_TREE_DEPTH
                else ()
            )
            return AustinTask(
                task_id=task_id,
                name=info.name,
                frames=info.frames,
                elapsed=info.elapsed,
                awaiting=awaiting,
            )

        owner = (pid, thread)
        roots = [
            task_id
            for task_id, info in self._task_info.items()
            if info.owner == owner and not has_parent(task_id)
        ]

        if not roots:
            # Best-effort fallback, matching austin's own render_tree: if
            # every one of this owner's tasks appears to have a parent (a
            # cyclic/bogus edge), there's no true root -- show each as its
            # own top-level tree rather than silently showing nothing.
            roots = [
                task_id
                for task_id, info in self._task_info.items()
                if info.owner == owner
            ]

        return tuple(build(task_id, 0) for task_id in roots)

    def get_kernel_frame(self, name: str) -> MojoKernelFrame:
        """Parse kernel frame."""
        return MojoKernelFrame(name)

    def _get_metric(self, metric_type: MojoMetricType, value: int) -> MojoMetric:
        metric = MojoMetric(metric_type, value)

        assert self._running_sample is not None, self._running_sample
        self._running_sample.metrics[metric_type] = metric

        return metric

    def get_time_metric(self, value: int) -> MojoMetric:
        """Parse time metric.

        A task stack's frame sequence has no length prefix on the wire -- its
        end is only knowable by the terminating MOJO_METRIC_TIME that always
        follows it (see mojo_event_handler__handle_task_stack_end), which is
        why this, rather than get_task_stack, is where finalization happens.
        """
        if self._running_task_stack is not None:
            self._finalize_task_stack(value)
            return MojoMetric(MojoMetricType.TIME, value)

        return self._get_metric(MojoMetricType.TIME, value)

    def get_memory_metric(self, value: int) -> MojoMetric:
        """Parse memory metric."""
        return self._get_metric(MojoMetricType.MEMORY, value)

    def get_invalid_frame(self) -> MojoSpecialFrame:
        """Parse invalid frame."""
        return MojoSpecialFrame("INVALID")

    def get_idle(self) -> MojoIdle:
        """Parse idle event."""
        assert self._running_sample is not None, self._running_sample
        self._running_sample.idle = True

        return MojoIdle()

    def get_gc(self) -> MojoSpecialFrame:
        """Parse a GC event."""
        assert self._running_sample is not None, self._running_sample
        self._running_sample.gc = True

        return MojoSpecialFrame("GC")

    def get_string(self, key: int, value: str) -> MojoString:
        """Parse a string."""
        self._string_map[self.ref(key)] = (string := MojoString(key, value))

        return string

    def get_string_ref(self, key: int) -> MojoStringReference:
        """Parse string reference."""
        return MojoStringReference(self._string_map[self.ref(key)])

    def unwind(self) -> None:
        """Read the MOJO file."""
        for _ in self:
            pass


class MojoStreamReader(BaseMojoStreamReader):
    """MOJO stream reader.

    Converts a stream of MOJO events into Austin events, that is samples and
    metadata.
    """

    def read(self, n: int = 1) -> bytes:
        """Read bytes from the MOJO file."""
        return self._read(self.mojo.read(n), n)

    def read_int(self) -> int:
        while True:
            if (n := self._int_reader.send(self.read())) is not None:
                return n

    def read_string(self) -> str:
        """Read a string from the MOJO file."""
        while True:
            if (s := self._str_reader.send(self.read())) is not None:
                return s

    @handles(MojoEvents.METADATA)
    def parse_metadata(self) -> MojoMetadata:
        """Parse metadata."""
        return self.get_metadata(self.read_string(), self.read_string())

    @handles(MojoEvents.STACK)
    def parse_stack(self) -> MojoStack:
        """Parse a stack."""
        assert self.mojo_version is not None
        return self.get_stack(
            pid=self.read_int(),
            iid=self.read_int() if self.mojo_version >= 3 else None,
            thread=self.read_string(),
        )

    @handles(MojoEvents.FRAME)
    def parse_frame(self) -> MojoFrame:
        """Parse a frame."""
        key = self.read_int()
        filename_index = self.read_int()
        scope_index = self.read_int()
        line = self.read_int()

        if self.mojo_version == 1:
            line_end = column = column_end = None
        else:
            line_end = self.read_int()
            column = self.read_int()
            column_end = self.read_int()

        return self.get_frame(
            key, filename_index, scope_index, line, line_end, column, column_end
        )

    @handles(MojoEvents.FRAME_REF)
    def parse_frame_ref(self) -> MojoFrameReference:
        """Parse a frame reference."""
        return self.get_frame_ref(self.read_int())

    @handles(MojoEvents.FRAME_KERNEL)
    def parse_kernel_frame(self) -> MojoKernelFrame:
        """Parse kernel frame."""
        return self.get_kernel_frame(self.read_string())

    def _parse_metric(self, metric_type: MojoMetricType) -> MojoMetric:
        return self._get_metric(metric_type, self.read_int())

    @handles(MojoEvents.METRIC_TIME)
    def parse_time_metric(self) -> MojoMetric:
        """Parse time metric."""
        return self.get_time_metric(self.read_int())

    @handles(MojoEvents.METRIC_MEMORY)
    def parse_memory_metric(self) -> MojoMetric:
        """Parse memory metric."""
        return self._parse_metric(MojoMetricType.MEMORY)

    @handles(MojoEvents.FRAME_INVALID)
    def parse_invalid_frame(self) -> MojoSpecialFrame:
        """Parse invalid frame."""
        return self.get_invalid_frame()

    @handles(MojoEvents.IDLE)
    def parse_idle(self) -> MojoIdle:
        """Parse idle event."""
        return self.get_idle()

    @handles(MojoEvents.GC)
    def parse_gc(self) -> MojoSpecialFrame:
        """Parse a GC event."""
        return self.get_gc()

    @handles(MojoEvents.STRING)
    def parse_string(self) -> MojoString:
        """Parse a string."""
        return self.get_string(key=self.read_int(), value=self.read_string())

    @handles(MojoEvents.STRING_REF)
    def parse_string_ref(self) -> MojoStringReference:
        """Parse string reference."""
        return self.get_string_ref(self.read_int())

    @handles(MojoEvents.STACK_REPEAT)
    def parse_stack_repeat(self) -> MojoStackRepeat:
        """Parse a stack repeat event."""
        return self.get_stack_repeat()

    @handles(MojoEvents.TASK_WAITER)
    def parse_task_waiter(self) -> MojoTaskWaiter:
        """Parse a task waiter edge."""
        return self.get_task_waiter(self.read_int(), self.read_int())

    @handles(MojoEvents.TASK_STACK)
    def parse_task_stack(self) -> MojoTaskStack:
        """Parse the header of a suspended task's coroutine-chain snapshot."""
        return self.get_task_stack(self.read_int(), self.read_int())

    def parse_event(self) -> t.Optional[MojoEvent]:
        """Parse a single event."""
        try:
            (event_id,) = self.read()
        except ValueError:
            return None

        try:
            event = t.cast(dict, self.__handlers__)[event_id](self)
            object.__setattr__(event, "raw", bytes(self._last_bytes))
            self._last_bytes.clear()
            return event
        except KeyError as exc:
            raise ValueError(
                f"Unhandled event: {event_id} (offset: {self._offset}, last read: {self._last_read})"
            ) from exc
        except Exception as exc:
            msg = f"Invalid byte sequence at offset {self._offset} (last read: {self._last_read})"
            raise MojoParseError(msg) from exc

    def parse(self) -> t.Iterator[MojoEvent]:
        """Parse the MOJO file.

        Produces a stream of events.
        """
        # Check the MOJO header
        if self.mojo_version is None:
            if self.read(3) != b"MOJ":
                raise ValueError("Not a MOJO stream")

            # Get the MOJO version
            self.mojo_version = self.read_int()

            # Store the header bytes
            self.header = bytes(self._last_bytes)
            self._last_bytes.clear()

        # Parse the MOJO events
        while True:
            if (e := self.parse_event()) is None:
                return
            yield e

    def unwind(self) -> None:
        """Read the MOJO file."""
        for _ in self:
            pass

    def __iter__(self) -> t.Iterator[AustinEvent]:
        """Iterate over the MOJO file."""
        for e in self.parse():
            if isinstance(e, MojoMetadata):
                yield AustinMetadata(e.key, e.value)
            elif isinstance(e, MojoStack):
                if self.samples:
                    yield self.samples[-1]
        if self._running_sample is not None:
            yield self._finalize_sample()

    def hexdump(
        self,
        start: int,
        end: int,
        highlight: t.Set[int] = set(),  # noqa: B006
    ) -> None:
        """Print a hexdump of the MOJO file."""
        self.mojo.seek(start)
        data = self.mojo.read(end - start)
        print(f"Hexdump from {start} ({start:02x}) to {end} ({end:02x}):")
        print("Offset  :", " ".join(f"{i:02x}" for i in range(16)), "| ASCII")
        print("--------", "-" * 48, "|", "-" * 16)
        for i in range(0, len(data), 16):
            # highlight the bytes at the given offset with bold yellow using ANSI escape codes
            line = " ".join(
                f"\033[1;33m{b:02x}\033[0m" if o in highlight else f"{b:02x}"
                for o, b in enumerate(data[i : i + 16], start + i)
            )
            rep = "".join(chr(b) if 32 <= b < 127 else "." for b in data[i : i + 16])
            print(f"{start + i:08x}: {line} | {rep}")


class AsyncMojoStreamReader(BaseMojoStreamReader):
    """Asynchronous MOJO stream reader.

    Converts a stream of MOJO events into Austin events, that is samples and
    metadata.
    """

    async def read(self, n: int = 1) -> bytes:
        """Read bytes from the MOJO file."""
        data = await t.cast(asyncio.StreamReader, self.mojo).read(n)
        return self._read(data, n)

    async def read_int(self) -> int:
        while True:
            if (n := self._int_reader.send(await self.read())) is not None:
                return n

    async def read_string(self) -> str:
        """Read a string from the MOJO file."""
        while True:
            if (s := self._str_reader.send(await self.read())) is not None:
                return s

    @handles(MojoEvents.METADATA)
    async def parse_metadata(self) -> MojoMetadata:
        """Parse metadata."""
        return self.get_metadata(await self.read_string(), await self.read_string())

    @handles(MojoEvents.STACK)
    async def parse_stack(self) -> MojoStack:
        """Parse a stack."""
        assert self.mojo_version is not None
        return self.get_stack(
            pid=await self.read_int(),
            iid=await self.read_int() if self.mojo_version >= 3 else None,
            thread=await self.read_string(),
        )

    @handles(MojoEvents.FRAME)
    async def parse_frame(self) -> MojoFrame:
        """Parse a frame."""
        key = await self.read_int()
        filename_index = await self.read_int()
        scope_index = await self.read_int()
        line = await self.read_int()

        if self.mojo_version == 1:
            line_end = column = column_end = None
        else:
            line_end = await self.read_int()
            column = await self.read_int()
            column_end = await self.read_int()

        return self.get_frame(
            key, filename_index, scope_index, line, line_end, column, column_end
        )

    @handles(MojoEvents.FRAME_REF)
    async def parse_frame_ref(self) -> MojoFrameReference:
        """Parse a frame reference."""
        return self.get_frame_ref(await self.read_int())

    @handles(MojoEvents.FRAME_KERNEL)
    async def parse_kernel_frame(self) -> MojoKernelFrame:
        """Parse kernel frame."""
        return self.get_kernel_frame(await self.read_string())

    async def _parse_metric(self, metric_type: MojoMetricType) -> MojoMetric:
        return self._get_metric(metric_type, await self.read_int())

    @handles(MojoEvents.METRIC_TIME)
    async def parse_time_metric(self) -> MojoMetric:
        """Parse time metric."""
        return self.get_time_metric(await self.read_int())

    @handles(MojoEvents.METRIC_MEMORY)
    async def parse_memory_metric(self) -> MojoMetric:
        """Parse memory metric."""
        return await self._parse_metric(MojoMetricType.MEMORY)

    @handles(MojoEvents.FRAME_INVALID)
    async def parse_invalid_frame(self) -> MojoSpecialFrame:
        """Parse invalid frame."""
        return self.get_invalid_frame()

    @handles(MojoEvents.IDLE)
    async def parse_idle(self) -> MojoIdle:
        """Parse idle event."""
        return self.get_idle()

    @handles(MojoEvents.GC)
    async def parse_gc(self) -> MojoSpecialFrame:
        """Parse a GC event."""
        return self.get_gc()

    @handles(MojoEvents.STRING)
    async def parse_string(self) -> MojoString:
        """Parse a string."""
        return self.get_string(
            key=await self.read_int(), value=await self.read_string()
        )

    @handles(MojoEvents.STRING_REF)
    async def parse_string_ref(self) -> MojoStringReference:
        """Parse string reference."""
        return self.get_string_ref(await self.read_int())

    @handles(MojoEvents.STACK_REPEAT)
    async def parse_stack_repeat(self) -> MojoStackRepeat:
        """Parse a stack repeat event."""
        return self.get_stack_repeat()

    @handles(MojoEvents.TASK_WAITER)
    async def parse_task_waiter(self) -> MojoTaskWaiter:
        """Parse a task waiter edge."""
        return self.get_task_waiter(await self.read_int(), await self.read_int())

    @handles(MojoEvents.TASK_STACK)
    async def parse_task_stack(self) -> MojoTaskStack:
        """Parse the header of a suspended task's coroutine-chain snapshot."""
        return self.get_task_stack(await self.read_int(), await self.read_int())

    async def parse_event(self) -> t.Optional[MojoEvent]:
        """Parse a single event."""
        try:
            (event_id,) = await self.read()
        except ValueError:
            return None

        try:
            event = await t.cast(dict, self.__handlers__)[event_id](self)
            object.__setattr__(event, "raw", bytes(self._last_bytes))
            self._last_bytes.clear()
            return event
        except KeyError as exc:
            raise ValueError(
                f"Unhandled event: {event_id} (offset: {self._offset}, last read: {self._last_read})"
            ) from exc
        except Exception as exc:
            msg = f"Invalid byte sequence at offset {self._offset} (last read: {self._last_read})"
            raise MojoParseError(msg) from exc

    async def parse(self) -> t.AsyncIterator[MojoEvent]:
        """Parse the MOJO file.

        Produces a stream of events.
        """
        # Check the MOJO header
        if self.mojo_version is None:
            if await self.read(3) != b"MOJ":
                raise ValueError("Not a MOJO stream")

            # Get the MOJO version
            self.mojo_version = await self.read_int()

            # Store the header bytes
            self.header = bytes(self._last_bytes)
            self._last_bytes.clear()

        # Parse the MOJO events
        while True:
            if (e := await self.parse_event()) is None:
                return
            yield e

    def unwind(self) -> None:
        """Read the MOJO file."""
        for _ in self:
            pass

    async def __aiter__(self) -> t.AsyncIterator[AustinEvent]:
        """Iterate over the MOJO file."""
        async for e in self.parse():
            if isinstance(e, MojoMetadata):
                yield AustinMetadata(e.key, e.value)
            elif isinstance(e, MojoStack):
                if self.samples:
                    yield self.samples[-1]
        if self._running_sample is not None:
            yield self._finalize_sample()


class BaseMojoStreamWriter(abc.ABC):
    """Base class for MOJO stream writers."""

    HEADER = b"MOJ\x04"

    def __init__(self, mojo: t.Any) -> None:
        self.mojo = mojo
        self._frames: t.Dict[AustinFrame, MojoFrame] = {}
        self._strings: t.Dict[str, MojoString] = {
            EMPTY.value: EMPTY,
            UNKNOWN.value: UNKNOWN,
        }

        self._meta: t.Dict[str, str] = {}

        self._mode: t.Optional[str] = None
        self._gc = False

        self._new_entries: t.List[MojoEvent] = []
        self._task_ids: t.Dict[int, int] = {}

    def set_metadata(self, metadata: AustinMetadata) -> None:
        self._meta[metadata.name] = metadata.value
        if metadata.name == "gc" and metadata.value == "on":
            self._gc = True
        elif metadata.name == "mode":
            self._mode = metadata.value

    def resolve_string(self, value: str) -> MojoString:
        try:
            return self._strings[value]
        except KeyError:
            self._strings[value] = mojo_string = MojoString(len(self._strings), value)
            self._new_entries.append(mojo_string)
            return mojo_string

    def resolve_task_id(self, task_id: int) -> int:
        try:
            return self._task_ids[task_id]
        except KeyError:
            compact_id = len(self._task_ids)
            self._task_ids[task_id] = compact_id
            return compact_id

    def resolve_frame(self, frame: AustinFrame) -> MojoFrame:
        try:
            return self._frames[frame]
        except KeyError:
            self._frames[frame] = mojo_frame = MojoFrame(
                len(self._frames),
                self.resolve_string(frame.filename),
                self.resolve_string(frame.function),
                frame.line,
                frame.line_end or 0,
                frame.column or 0,
                frame.column_end or 0,
            )
            self._new_entries.append(mojo_frame)
            return mojo_frame

    def _collect_tasks(
        self,
        tasks: t.Sequence[AustinTask],
        seen: t.Dict[int, AustinTask],
        edges: t.Dict[int, t.Set[int]],
    ) -> None:
        """Flatten a root-task list into its distinct tasks and waiter edges.

        A task can legitimately appear more than once (once per waiter, if
        it has more than one -- see AustinTask's own docstring on
        ``awaiting``), so this collects each task_id's own stack exactly
        once (``seen``, first occurrence wins) and every one of its waiters
        together (``edges``), rather than re-walking and re-emitting it once
        per occurrence.
        """
        for task in tasks:
            seen.setdefault(task.task_id, task)
            for awaited in task.awaiting:
                edges.setdefault(awaited.task_id, set()).add(task.task_id)
            self._collect_tasks(task.awaiting, seen, edges)

    def write_tasks(self, tasks: t.Sequence[AustinTask]) -> int:
        """Write every task's own coroutine-chain snapshot, then every waiter edge.

        See _collect_tasks for why each is written exactly once, and edges
        for one task_id are always written contiguously (required for
        MojoStreamReader.get_task_waiter's own batch-replace logic to
        reconstruct a multi-waiter task correctly).
        """
        size = 0

        seen: t.Dict[int, AustinTask] = {}
        edges: t.Dict[int, t.Set[int]] = {}
        self._collect_tasks(tasks, seen, edges)

        for task in seen.values():
            name_key = self.resolve_string(task.name).key if task.name else 0

            while self._new_entries:
                size += self.mojo.write(self._new_entries.pop(0).to_bytes())

            size += self.mojo.write(
                MojoTaskStack(
                    task_id=self.resolve_task_id(task.task_id), name_key=name_key
                ).to_bytes()
            )

            task_frames = [self.resolve_frame(f) for f in task.frames]

            while self._new_entries:
                size += self.mojo.write(self._new_entries.pop(0).to_bytes())

            for frame in task_frames:
                size += self.mojo.write(MojoFrameReference(frame).to_bytes())

            size += self.mojo.write(
                MojoMetric(MojoMetricType.TIME, task.elapsed or 0).to_bytes()
            )

        for task_id, waiter_ids in edges.items():
            compact_task_id = self.resolve_task_id(task_id)
            for waiter_id in waiter_ids:
                size += self.mojo.write(
                    MojoTaskWaiter(
                        task_id=compact_task_id,
                        waiter_id=self.resolve_task_id(waiter_id),
                    ).to_bytes()
                )

        return size

    @abc.abstractmethod
    def write(self, event: AustinEvent) -> int: ...  # noqa: E704


class MojoStreamWriter(BaseMojoStreamWriter):
    """MOJO stream writer."""

    def __init__(self, mojo: t.BinaryIO) -> None:
        super().__init__(mojo)

        mojo.write(self.HEADER)

    def write(self, event: AustinEvent) -> int:
        size = 0

        if isinstance(event, AustinMetadata):
            self.set_metadata(event)
            size += self.mojo.write(
                MojoMetadata(key=event.name, value=event.value).to_bytes()
            )

        elif isinstance(event, AustinSample):
            size += self.mojo.write(
                MojoStack(
                    pid=event.pid, iid=event.iid or 0, tid=event.thread
                ).to_bytes()
            )

            # Task-scan payload (waiter edges + suspended coroutine-chain
            # snapshots) is written before this sample's own frames -- it
            # rides between the enclosing MOJO_STACK header and the sample's
            # own frame dump on the real wire too (see austin's own
            # py_proc.c, _py_proc__sample_threads).
            if event.tasks:
                size += self.write_tasks(event.tasks)

            frames = (
                [self.resolve_frame(f) for f in event.frames] if event.frames else []
            )

            while self._new_entries:
                size += self.mojo.write(self._new_entries.pop(0).to_bytes())

            for frame in frames:
                size += self.mojo.write(MojoFrameReference(frame).to_bytes())

            if event.gc:
                size += self.mojo.write(bytes([MojoEvents.GC]))

            if self._mode == "full":
                if event.idle:
                    size += self.mojo.write(bytes([MojoEvents.IDLE]))
                size += self.mojo.write(
                    MojoMetric(MojoMetricType.TIME, event.metrics.time or 0).to_bytes()
                )
                size += self.mojo.write(
                    MojoMetric(
                        MojoMetricType.MEMORY, event.metrics.memory or 0
                    ).to_bytes()
                )
            elif self._mode == "memory":
                size += self.mojo.write(
                    MojoMetric(
                        MojoMetricType.MEMORY, event.metrics.memory or 0
                    ).to_bytes()
                )
            else:
                size += self.mojo.write(
                    MojoMetric(MojoMetricType.TIME, event.metrics.time or 0).to_bytes()
                )

        else:
            msg = f"Unhandled event type {type(event)}"
            raise TypeError(msg)

        return size
