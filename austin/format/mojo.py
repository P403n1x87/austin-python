import abc
import asyncio
import io
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
from austin.events import InterpreterId
from austin.events import ProcessId
from austin.events import ThreadName


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

    def ref(self) -> int:
        return getattr(self, fields(self)[0].name)

    def to_bytes(self) -> bytes:
        buffer = bytearray([self.EVENT_ID])
        for f in fields(self):
            value = getattr(self, f.name)
            field_type = (
                f.type.__args__[0]
                if isinstance(f.type, t._UnionGenericAlias)
                else f.type
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
                MojoEvents.METRIC_TIME
                if self.metric_type is MojoMetricType.TIME
                else MojoEvents.METRIC_MEMORY
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
                frames=tuple(
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
                else None,
                gc=self._running_sample.gc,
                idle=self._running_sample.idle,
            )
        )

        self._running_sample = None

        return sample

    def get_stack(self, pid: int, iid: t.Optional[int], thread: str) -> MojoStack:
        """Parse a stack."""
        if self._running_sample is not None:
            self._finalize_sample()

        self._running_sample = _RunningSample(pid=pid, iid=iid, thread=thread)

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

        assert self._running_sample is not None, self._running_sample
        self._running_sample.frames.append(frame)

        return MojoFrameReference(frame)

    def get_kernel_frame(self, name: str) -> MojoKernelFrame:
        """Parse kernel frame."""
        return MojoKernelFrame(name)

    def _get_metric(self, metric_type: MojoMetricType, value: int) -> MojoMetric:
        metric = MojoMetric(metric_type, value)

        assert self._running_sample is not None, self._running_sample
        self._running_sample.metrics[metric_type] = metric

        return metric

    def get_time_metric(self, value: int) -> MojoMetric:
        """Parse time metric."""
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
        return self._parse_metric(MojoMetricType.TIME)

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

    def hexdump(self, start: int, end: int, highlight: t.Set[int] = set()) -> None:  # noqa: B006
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
        return await self._parse_metric(MojoMetricType.TIME)

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
    HEADER = b"MOJ\x03"

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

    @abc.abstractmethod
    def write(self, event: AustinEvent) -> int: ...


class MojoStreamWriter(BaseMojoStreamWriter):
    def __init__(self, mojo: io.BytesIO):
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
            frames = (
                [self.resolve_frame(f) for f in event.frames] if event.frames else []
            )

            size += self.mojo.write(
                MojoStack(
                    pid=event.pid, iid=event.iid or 0, tid=event.thread
                ).to_bytes()
            )

            while self._new_entries:
                size += self.mojo.write(self._new_entries.pop(0).to_bytes())

            for frame in frames:
                size += self.mojo.write(MojoFrameReference(frame).to_bytes())

            if self._gc:
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
