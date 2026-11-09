from contextlib import contextmanager
from contextlib import nullcontext
from enum import Enum
import os
from pathlib import Path
import sys
import threading
import typing as t

from austin.events import AustinEventIterator

MOJO_MAGIC = b"MOJ"

ProgressCallback = t.Callable[[float], None]


class Mode(Enum):
    """Austin profiling mode."""

    CPU = 0
    WALL = 1
    MEMORY = 2
    FULL = 3

    @classmethod
    def from_metadata(cls, mode: str) -> "Mode":
        """Get mode from metadata information."""
        return {
            "cpu": Mode.CPU,
            "wall": Mode.WALL,
            "memory": Mode.MEMORY,
            "full": Mode.FULL,
        }[mode]


@contextmanager
def file_progress(
    f: t.IO, on_progress: ProgressCallback, interval: float = 0.5
) -> t.Iterator[None]:
    """Report the fraction of a file that has been read.

    The ``on_progress`` callback is called periodically from a background
    thread, and once with ``1.0`` when the context exits normally. The file
    position is read from the OS, so this works with any reader of the file.
    """
    size = os.fstat(f.fileno()).st_size

    def report() -> None:
        while not done.wait(interval):
            on_progress(os.lseek(f.fileno(), 0, os.SEEK_CUR) / size if size else 1.0)

    done = threading.Event()
    reporter = threading.Thread(target=report, daemon=True)
    reporter.start()
    try:
        yield
    finally:
        done.set()
        reporter.join()

    on_progress(1.0)


def stderr_progress(label: str) -> t.Optional[ProgressCallback]:
    """Get a progress callback that prints to stderr, if it is a terminal."""
    if not sys.stderr.isatty():
        return None

    def on_progress(fraction: float) -> None:
        line = f"{label} {fraction:.0%}"
        if fraction >= 1.0:
            # Done: clear the progress line
            line = " " * len(line)
        print(f"\r{line}\r", end="", file=sys.stderr, flush=True)

    return on_progress


@contextmanager
def open_profile(
    path: t.Union[str, Path], on_progress: t.Optional[ProgressCallback] = None
) -> t.Iterator[AustinEventIterator]:
    """Open a MOJO or a collapsed stack profile file.

    The format is detected from the content of the file. The returned event
    iterator is only valid within the context. If ``on_progress`` is given, it
    is called with the fraction of the file read so far (see `file_progress`).
    """
    from austin.format.collapsed_stack import AustinFileReader
    from austin.format.mojo import MojoStreamReader

    with open(path, "rb") as f:
        is_mojo = f.read(len(MOJO_MAGIC)) == MOJO_MAGIC

    with open(path, "rb" if is_mojo else "r") as f:
        with file_progress(f, on_progress) if on_progress else nullcontext():
            yield (
                MojoStreamReader(f)
                if is_mojo
                else AustinFileReader(t.cast(t.TextIO, f))
            )
