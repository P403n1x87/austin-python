from pathlib import Path

from austin.events import AustinSample
from austin.format.collapsed_stack import AustinFileReader


def test_austin_file_reader(datapath: Path) -> None:
    with AustinFileReader((datapath / "austin.out").open()) as fr:
        assert (
            sum(bool(sample) for sample in fr if isinstance(sample, AustinSample)) == 73
        )

        assert fr.metadata == {
            "austin": "3.0.0",
            "interval": "10000",
            "mode": "wall",
            "duration": "383010",
        }
