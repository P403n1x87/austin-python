from enum import Enum


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
