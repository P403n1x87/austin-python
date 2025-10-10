import typing as t
from functools import singledispatchmethod
from pathlib import Path

from austin.events import AustinEvent
from austin.events import AustinEventIterator
from austin.events import AustinFrame
from austin.events import AustinMetadata
from austin.events import AustinMetrics
from austin.events import AustinSample
from austin.format.mojo import MojoStreamReader


__version__ = "0.1.0"


class InvalidFrame(Exception):
    """Raised when a frame is invalid."""

    def __init__(self, frame: str) -> None:
        super().__init__(f"Invalid frame: {frame}")
        self.frame = frame


class InvalidSample(Exception):
    """Raised when a sample is invalid."""

    def __init__(self, sample: str) -> None:
        super().__init__(f"Invalid sample: {sample}")
        self.sample = sample


def parse_frame(frame: str) -> AustinFrame:
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
        filename, function, line = frame.rsplit(":", maxsplit=2)
    except ValueError:
        raise InvalidFrame(frame) from None
    return AustinFrame(filename=filename, function=function, line=int(line or 0))


def parse_collapsed_stack(sample: str) -> AustinSample:
    """Parse the given string as a sample.

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

    thread, _, frames_data = rest.partition(";")
    thread = thread[1:]
    iid = None
    if ":" in thread:
        iid, _, thread = thread.partition(":")

    frames = (
        tuple(parse_frame(frame) for frame in frames_data.split(";"))
        if frames_data
        else None
    )

    if "," in metrics:
        time, idle, memory = metrics.split(",")
    else:
        time, idle, memory = metrics, None, None

    return AustinSample(
        pid=int(pid),
        iid=int(iid) if iid else None,
        thread=thread,
        metrics=AustinMetrics(
            time=int(time) if time else None,
            memory=int(memory) if memory else None,
        ),
        frames=frames,
        idle=bool(int(idle)) if idle else None,
        gc=any(frame.function == "GC" for frame in frames) if frames else None,
    )


class AustinFileReader(AustinEventIterator):
    """Austin file reader.

    Conveniently read an Austin sample file by also parsing any header and
    footer metadata.
    """

    def __init__(self, stream: t.TextIO) -> None:
        self.metadata: t.Dict[str, str] = {}
        self.stream: t.TextIO = stream

    def __enter__(self) -> "AustinFileReader":
        """Open the Austin file and read the metadata."""
        return self

    def __iter__(self) -> t.Iterator[AustinEvent]:
        """Iterator over the samples in the Austin file."""
        for line in self.stream:
            if not line:
                break
            line = line.rstrip("\n")
            if not line:
                continue
            if line.startswith("# "):
                key, _, value = line[2:].strip().partition(": ")
                self.metadata[key] = value
                yield AustinMetadata(name=key, value=value)
            else:
                yield parse_collapsed_stack(line)

    def __exit__(self, *args: t.Any) -> None:
        """Close the Austin file."""
        self.stream.flush()


class AustinEventCollapsedStackFormatter:
    """Formatter for Austin events in collapsed stack format."""

    def __init__(self, mode: t.Optional[str] = None) -> None:
        self.mode = mode

    @singledispatchmethod
    def format(self, event) -> str:
        """Format an Austin event to a string."""
        raise NotImplementedError(f"Cannot format event of type {type(event)}")

    @format.register(AustinMetadata)
    def _(self, event: AustinMetadata) -> str:
        """Format Austin metadata event to a string."""
        if event.name == "mode":
            self.mode = event.value
        return f"# {event.name}: {event.value}"

    @format.register(AustinFrame)
    def _(self, event: AustinFrame) -> str:
        """Format Austin frame event to a string."""
        return f"{event.filename}:{event.function}:{event.line}"

    @format.register(AustinSample)
    def _(self, event: AustinSample) -> str:
        """Format Austin sample event to a string."""
        assert self.mode is not None

        try:
            thread = str(int(event.thread, 16))
        except ValueError:
            # Fallback: use the original string if not a valid hex, or try base 10
            thread = event.thread

        head = (
            f"P{event.pid};T{event.iid}:{thread}"
            if event.iid is not None
            else f"P{event.pid};T{thread}"
        )
        frames = (
            ";".join(self.format(frame) for frame in event.frames)
            if event.frames is not None
            else None
        )
        if self.mode == "full":
            assert event.idle is not None
            tail = f"{event.metrics.time},{int(event.idle)},{event.metrics.memory}"
        if self.mode == "memory":
            tail = str(event.metrics.memory)
        else:
            tail = str(event.metrics.time)

        return f"{head};{frames} {tail}" if frames is not None else f"{head} {tail}"


def mojo2austin(args: t.Any) -> None:
    with args.input.open("rb") as mojo, args.output.open("w") as fout:
        formatter = AustinEventCollapsedStackFormatter()
        for event in MojoStreamReader(mojo):
            print(formatter.format(event), file=fout)


def main() -> None:
    from argparse import ArgumentParser

    arg_parser = ArgumentParser(
        prog="mojo2austin",
        description="Convert MOJO files to Austin format.",
    )

    arg_parser.add_argument(
        "input",
        type=Path,
        help="The MOJO file to convert",
    )
    arg_parser.add_argument(
        "output",
        type=Path,
        help="The name of the output Austin file.",
    )

    arg_parser.add_argument("-V", "--version", action="version", version=__version__)

    args = arg_parser.parse_args()

    try:
        mojo2austin(args)
    except FileNotFoundError:
        print(f"No such input file: {args.input}")
        exit(1)


if __name__ == "__main__":
    main()
