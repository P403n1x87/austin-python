import json
from pathlib import Path

import pytest

from austin.events import AustinFrame
from austin.events import AustinMetadata
from austin.events import AustinMetrics
from austin.events import AustinSample
from austin.format.mojo import MojoStreamWriter
from austin.tools.query import main


def _sample(stack: str, time: int, gc: bool = False) -> AustinSample:
    frames = []
    for frame in stack.split(";"):
        filename, function, line = frame.rsplit(":", 2)
        frames.append(AustinFrame(filename, function, int(line)))
    return AustinSample(
        pid=1,
        iid=0,
        thread="t1",
        metrics=AustinMetrics(time=time),
        frames=tuple(frames),
        gc=gc,
    )


@pytest.fixture
def profile(tmp_path: Path) -> Path:
    path = tmp_path / "profile.mojo"
    with path.open("wb") as f:
        writer = MojoStreamWriter(f)
        writer.write(AustinMetadata("mode", "wall"))
        writer.write(AustinMetadata("gc", "on"))
        writer.write(_sample("/app/a.py:main:1;/app/a.py:loop:2", 10))
        writer.write(_sample("/app/a.py:main:1;/app/b.py:work:3", 30))
        writer.write(_sample("/app/a.py:main:1;/app/a.py:collect:4", 5, gc=True))
    return path


def test_help_explains_selectors_and_workflow(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    assert "file:func:line" in out
    assert "task-stacks" in out
    assert "typical workflow" in out


def test_json_is_compact(profile, capsys):
    assert main([str(profile), "top", "-n", "1", "--json"]) == 0
    out = capsys.readouterr().out
    assert "\n" not in out.strip()
    assert json.loads(out)["entries"][0]["location"] == "/app/b.py:work"


def test_gc_filters(profile, capsys):
    assert main([str(profile), "top", "--gc"]) == 0
    out = capsys.readouterr().out
    assert "collect" in out and "work" not in out

    assert main([str(profile), "top", "--no-gc"]) == 0
    out = capsys.readouterr().out
    assert "work" in out and "collect" not in out


def test_options_after_the_command(profile, capsys):
    assert main([str(profile), "callers", "work", "--thread", "t1"]) == 0
    assert "a.py:main" in capsys.readouterr().out


def test_no_samples_match(profile, capsys):
    assert main([str(profile), "top", "--thread", "nope"]) == 1
    assert "no samples match the filters" in capsys.readouterr().err


def test_errors(profile, capsys, tmp_path):
    assert main([str(profile), "callers", "wrok"]) == 1
    assert "did you mean one of: work" in capsys.readouterr().err

    assert main([str(profile), "tasks", "--task", "x"]) == 1
    assert "has no asyncio tasks" in capsys.readouterr().err

    assert main([str(profile), "top", "--metric", "memory"]) == 1
    assert "not available in wall mode" in capsys.readouterr().err

    assert main([str(tmp_path / "missing.mojo"), "summary"]) == 1
    assert "cannot read" in capsys.readouterr().err


@pytest.mark.parametrize(
    "command",
    [
        ["summary"],
        ["top", "--by", "total", "--lines"],
        ["find", "a.py"],
        ["lines", "main"],
        ["stacks", "--per-thread"],
        ["callees", "main"],
        ["tree", "main", "--max-depth", "1"],
        ["tasks"],
        ["task-stacks"],
    ],
)
def test_commands(profile, capsys, command):
    assert main([str(profile), *command]) == 0
    assert capsys.readouterr().out.startswith(("metric:", "mode:"))
