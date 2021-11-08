from austin.stats import AustinFileReader
from austin.stats import MetricType
from austin.stats import Sample


def test_austin_file_reader(datapath):
    with AustinFileReader(datapath / "austin.out") as fr:
        assert fr.metadata == {
            "austin": "3.0.0",
            "interval": "10000",
            "mode": "wall",
        }

        assert sum(bool(Sample.parse(line, MetricType.TIME)) for line in fr) == 73

        assert fr.metadata == {
            "austin": "3.0.0",
            "interval": "10000",
            "mode": "wall",
            "duration": "383010",
        }
