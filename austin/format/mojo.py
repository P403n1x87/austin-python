import typing as t
from dataclasses import dataclass
from enum import Enum
from io import BufferedReader


__version__ = "0.1.0"


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


def handles(
    e: int,
) -> t.Callable[[t.Callable[["MojoFile"], t.Generator]], MojoEventHandler]:
    """MOJO handler registration decorator."""

    def _(f: t.Callable[["MojoFile"], t.Generator]) -> MojoEventHandler:
        t.cast(MojoEventHandler, f).__event__ = e
        return t.cast(MojoEventHandler, f)

    return _


class MojoMetricType(Enum):
    """MOJO metric types."""

    TIME = 0
    MEMORY = 1


class MojoEvent:
    """MOJO event."""

    def __init__(self) -> None:
        """Initialize the event."""
        self.raw = bytes([])

    def to_austin(self) -> str:
        """Convert the event to Austin format."""
        return ""


@dataclass
class MojoString(MojoEvent):
    """MOJO string."""

    key: int
    value: str


@dataclass
class MojoStringReference(MojoEvent):
    """MOJO string reference."""

    string: MojoString

    def to_austin(self) -> str:
        """Convert the event to Austin format."""
        return self.string.value


class MojoIdle(MojoEvent):
    """MOJO idle event."""

    pass


@dataclass
class MojoMetadata(MojoEvent):
    """MOJO metadata."""

    key: str
    value: str

    def to_austin(self) -> str:
        """Convert the event to Austin format."""
        return f"# {self.key}: {self.value}\n"


@dataclass
class MojoStack(MojoEvent):
    """MOJO stack."""

    pid: int
    tid: str

    def to_austin(self) -> str:
        """Convert the event to Austin format."""
        return f"P{self.pid};T{int(self.tid, 16)}"


@dataclass
class MojoFrame(MojoEvent):
    """MOJO frame."""

    key: int
    filename: MojoStringReference
    scope: MojoStringReference
    line: int


@dataclass
class MojoKernelFrame(MojoEvent):
    """MOJO kernel frame."""

    scope: str

    def to_austin(self) -> str:
        """Convert the event to Austin format."""
        return f";kernel:{self.scope}:0"


@dataclass
class MojoSpecialFrame(MojoEvent):
    """MOJO special frame."""

    label: str

    def to_austin(self) -> str:
        """Convert the event to Austin format."""
        return f";:{self.label}:"


@dataclass
class MojoFrameReference(MojoEvent):
    """MOJO frame reference."""

    frame: MojoFrame

    def to_austin(self) -> str:
        """Convert the event to Austin format."""
        return f";{self.frame.filename.to_austin()}:{self.frame.scope.to_austin()}:{self.frame.line}"


@dataclass
class MojoMetric(MojoEvent):
    """MOJO metric."""

    metric_type: MojoMetricType
    value: int

    def to_austin(self) -> str:
        """Convert the metric to Austin format."""
        return f" {self.value}\n"


@dataclass
class MojoFullMetrics(MojoEvent):
    """MOJO full metrics."""

    metrics: t.List[t.Union[MojoMetric, int]]

    def to_austin(self) -> str:
        """Convert the event to Austin format."""
        if len(self.metrics) == 3:
            time, idle, memory = self.metrics
            assert idle == 1, self.metrics
        else:
            time, memory = self.metrics
            idle = 0

        return f" {t.cast(MojoMetric,time).value},{idle},{t.cast(MojoMetric, memory).value}\n"


UNKNOWN = MojoString(1, "<unknown>")


class MojoFile:
    """MOJO file."""

    __handlers__: t.Optional[t.Dict[int, t.Callable[[], None]]] = None

    def __init__(self, mojo: BufferedReader) -> None:
        if self.__handlers__ is None:
            self.__class__.__handlers__ = {
                f.__event__: f
                for f in self.__class__.__dict__.values()
                if hasattr(f, "__event__")
            }

        self.mojo = mojo
        self._metrics: t.List[t.Union[MojoMetric, int]] = []
        self._full_mode = False
        self._frame_map: t.Dict[t.Tuple[int, int], MojoFrame] = {}
        self._offset = 0
        self._last_read = 0
        self._last_bytes = bytearray()
        self._string_map: t.Dict[t.Tuple[int, int], MojoString] = {}
        self._pid: t.Optional[int] = None

        if self.read(3) != b"MOJ":
            raise ValueError("Not a MOJO file")

        self.mojo_version = self.read_int()

        self.header = bytes(self._last_bytes)
        self._last_bytes.clear()

    def ref(self, n: int) -> t.Tuple[int, int]:
        """Return a per-process reference key.

        MOJO objects that carry a numeric reference is to be interpreted as
        relative to the current process, so it has to be combined with the
        last seen PID.
        """
        pid = self._pid
        assert pid is not None, pid

        return (pid, n)

    def read(self, n: int) -> bytes:
        """Read bytes from the MOJO file."""
        self._offset += self._last_read
        self._last_read = n

        bytes = self.mojo.read(n)

        self._last_bytes.extend(bytes)

        return bytes

    def read_int(self) -> int:
        """Read an integer from the MOJO file."""
        n = 0
        s = 6
        (b,) = self.read(1)
        n |= b & 0x3F
        sign = b & 0x40
        while b & 0x80:
            (b,) = self.read(1)
            n |= (b & 0x7F) << s
            s += 7
        return -n if sign else n

    def read_until(self, until: bytes = b"\0") -> bytes:
        """Read until a given byte is found."""
        buffer = bytearray()
        while True:
            b = self.read(1)
            if not b or b == until:
                return bytes(buffer)
            buffer += b

    def read_string(self) -> str:
        """Read a string from the MOJO file."""
        return self.read_until().decode()

    def _emit_metrics(self) -> t.Generator[t.Union[MojoEvent, int], None, None]:
        """Emit metrics."""
        if self._metrics:
            yield MojoFullMetrics(
                self._metrics
            ) if self._full_mode else self._metrics.pop()
            self._metrics.clear()

    @handles(MojoEvents.METADATA)
    def parse_metadata(self) -> t.Generator[t.Union[MojoEvent, int], None, None]:
        """Parse metadata."""
        yield from self._emit_metrics()

        metadata = MojoMetadata(self.read_string(), self.read_string())
        if metadata.key == "mode" and metadata.value == "full":
            self._full_mode = True
        yield metadata

    @handles(MojoEvents.STACK)
    def parse_stack(self) -> t.Generator[t.Union[MojoEvent, int], None, None]:
        """Parse a stack."""
        yield from self._emit_metrics()

        self._pid = pid = self.read_int()
        yield MojoStack(pid, self.read_string())

    def _lookup_string(self) -> MojoString:
        n = self.read_int()
        if n == 1:
            return UNKNOWN

        return self._string_map[self.ref(n)]

    @handles(MojoEvents.FRAME)
    def parse_frame(self) -> t.Generator[MojoFrame, None, None]:
        """Parse a frame."""
        frame_key = self.read_int()
        filename = MojoStringReference(self._lookup_string())
        scope = MojoStringReference(self._lookup_string())
        line = self.read_int()

        frame = MojoFrame(frame_key, filename, scope, line)

        self._frame_map[self.ref(frame_key)] = frame

        yield frame

    @handles(MojoEvents.FRAME_REF)
    def parse_frame_ref(self) -> t.Generator[MojoFrameReference, None, None]:
        """Parse a frame reference."""
        yield MojoFrameReference(self._frame_map[self.ref(self.read_int())])

    @handles(MojoEvents.FRAME_KERNEL)
    def parse_kernel_frame(self) -> t.Generator[MojoKernelFrame, None, None]:
        """Parse kernel frame."""
        yield MojoKernelFrame(self.read_string())

    def _parse_metric(self, metric_type: MojoMetricType) -> MojoEvent:
        metric = MojoMetric(
            metric_type,
            self.read_int(),
        )

        if self._full_mode:
            self._metrics.append(metric)
            return MojoEvent()

        return metric

    @handles(MojoEvents.METRIC_TIME)
    def parse_time_metric(self) -> t.Generator[MojoEvent, None, None]:
        """Parse time metric."""
        yield self._parse_metric(MojoMetricType.TIME)

    @handles(MojoEvents.METRIC_MEMORY)
    def parse_memory_metric(self) -> t.Generator[MojoEvent, None, None]:
        """Parse memory metric."""
        yield self._parse_metric(MojoMetricType.MEMORY)

    @handles(MojoEvents.FRAME_INVALID)
    def parse_invalid_frame(self) -> t.Generator[MojoSpecialFrame, None, None]:
        """Parse invalid frame."""
        yield MojoSpecialFrame("INVALID")

    @handles(MojoEvents.IDLE)
    def parse_idle(self) -> t.Generator[MojoIdle, None, None]:
        """Parse idle event."""
        self._metrics.append(1)
        yield MojoIdle()

    @handles(MojoEvents.GC)
    def parse_gc(self) -> t.Generator[MojoSpecialFrame, None, None]:
        """Parse a GC event."""
        yield MojoSpecialFrame("GC")

    @handles(MojoEvents.STRING)
    def parse_string(self) -> t.Generator[MojoString, None, None]:
        """Parse a string."""
        key = self.read_int()
        value = self.read_string()

        string = MojoString(key, value)

        self._string_map[self.ref(key)] = string

        yield string

    @handles(MojoEvents.STRING_REF)
    def parse_string_ref(self) -> t.Generator[MojoStringReference, None, None]:
        """Parse string reference."""
        assert self._pid, self._pid
        yield MojoStringReference(self._string_map[self.ref(self.read_int())])

    def parse_event(self) -> t.Generator[t.Optional[MojoEvent], None, None]:
        """Parse a single event."""
        try:
            (event_id,) = self.read(1)
        except ValueError:
            yield None
            return

        try:
            for event in t.cast(dict, self.__handlers__)[event_id](self):
                event.raw = bytes(self._last_bytes)
                self._last_bytes.clear()
                yield event
        except KeyError as exc:
            raise ValueError(
                f"Unhandled event: {event_id} (offset: {self._offset}, last read: {self._last_read})"
            ) from exc

    def parse(self) -> t.Iterator[MojoEvent]:
        """Parse the MOJO file.

        Produces a stream of events.
        """
        while True:
            for e in self.parse_event():
                if e is None:
                    return
                yield e


def main() -> None:
    from argparse import ArgumentParser

    arg_parser = ArgumentParser(
        prog="mojo2austin",
        description="Convert MOJO files to Austin format.",
    )

    arg_parser.add_argument(
        "input",
        type=str,
        help="The MOJO file to convert",
    )
    arg_parser.add_argument(
        "output", type=str, help="The name of the output Austin file."
    )

    arg_parser.add_argument("-V", "--version", action="version", version=__version__)

    args = arg_parser.parse_args()

    try:
        with open(args.input, "rb") as mojo, open(args.output, "w") as fout:
            for event in MojoFile(mojo).parse():
                fout.write(event.to_austin())

    except FileNotFoundError:
        print(f"No such input file: {args.input}")
        exit(1)


if __name__ == "__main__":
    main()
