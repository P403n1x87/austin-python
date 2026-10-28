from contextlib import contextmanager
from enum import Enum
from pathlib import Path
import typing as t

from austin.events import AustinEventIterator

MOJO_MAGIC = b"MOJ"


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
def open_profile(path: t.Union[str, Path]) -> t.Iterator[AustinEventIterator]:
    """Open a MOJO or a collapsed stack profile file.

    The format is detected from the content of the file. The returned event
    iterator is only valid within the context.
    """
    from austin.format.collapsed_stack import AustinFileReader
    from austin.format.mojo import MojoStreamReader

    with open(path, "rb") as f:
        is_mojo = f.read(len(MOJO_MAGIC)) == MOJO_MAGIC

    if is_mojo:
        with open(path, "rb") as f:
            yield MojoStreamReader(f)
    else:
        with open(path) as f:
            yield AustinFileReader(f)
