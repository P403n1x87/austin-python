import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from austin.query import Location
from austin.query import ProfileQuery
from austin.tools.query import main

AUSTIN = shutil.which("austin")

pytestmark = [
    pytest.mark.skipif(AUSTIN is None, reason="austin not found"),
    pytest.mark.skipif(
        sys.version_info < (3, 14), reason="asyncio tasks require Python 3.14+"
    ),
]

TARGET = """
import asyncio


def cpu_burst(n):
    total = 0
    for i in range(n):
        total += (i * i) % 97
    return total


async def worker(n):
    for _ in range(20):
        cpu_burst(200_000)
        await asyncio.sleep(0)
    return n


async def main():
    tasks = [asyncio.create_task(worker(i), name=f"worker-{i}") for i in range(2)]
    await asyncio.gather(*tasks)


asyncio.run(main())
"""


@pytest.fixture(scope="module")
def profile(tmp_path_factory: pytest.TempPathFactory) -> Path:
    folder = tmp_path_factory.mktemp("query")
    target = folder / "target_query.py"
    target.write_text(TARGET)
    output = folder / "profile.mojo"

    assert AUSTIN is not None
    result = subprocess.run(
        [AUSTIN, "-c", "-i", "1ms", "-o", str(output), sys.executable, str(target)],
        capture_output=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")

    return output


def test_running_task_code_is_in_the_thread_queries(profile: Path) -> None:
    q = ProfileQuery.from_file(profile)
    assert q.mode == "cpu"

    (hottest,) = q.top(1)
    assert hottest.location.function == "cpu_burst"
    assert hottest.own_pct > 50

    callers = q.callers("cpu_burst")
    assert callers[0].location.function == "worker"


def test_tasks(profile: Path) -> None:
    q = ProfileQuery.from_file(profile)

    workers = {
        node.name: node
        for root in q.tasks()
        for node in root.children
        if node.name is not None and node.name.startswith("worker-")
    }
    assert sorted(workers) == ["worker-0", "worker-1"]

    total = q.summary().profile_total
    for node in workers.values():
        assert node.awaiting == 0  # No await time in CPU mode
        assert node.running > total / 5

    worker = q.filter(task="worker-0")
    assert worker.top(1)[0].location == Location(
        str(profile.parent / "target_query.py"), "cpu_burst"
    )
    assert worker.summary().profile_total == workers["worker-0"].running


def test_cli(profile: Path, capsys: pytest.CaptureFixture) -> None:
    assert main([str(profile), "top", "-n", "1", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["entries"][0]["location"].endswith(":cpu_burst")

    assert main([str(profile), "tasks", "--task", "worker-1"]) == 0
    assert "worker-1" in capsys.readouterr().out

    assert main([str(profile), "task-stacks", "worker-0", "-n", "1"]) == 0
    out = capsys.readouterr().out
    assert "tasks: worker-0" in out and "cpu_burst" in out

    assert main([str(profile), "callers", "cpu_brst"]) == 1
    assert "did you mean" in capsys.readouterr().err

    assert main([str(profile), "top", "--task", "worker0"]) == 1
    assert "did you mean one of: worker-0" in capsys.readouterr().err
