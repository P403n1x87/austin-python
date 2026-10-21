# This file is part of "austin-python" which is released under GPL.
#
# See file LICENCE or go to http://www.gnu.org/licenses/ for full license
# details.
#
# austin-python is a Python wrapper around Austin, the CPython frame stack
# sampler.
#
# Copyright (c) 2018-2022 Gabriele N. Tornetta <phoenix1987@gmail.com>.
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import asyncio
import sys
import tempfile
import typing as t
from io import BytesIO
from pathlib import Path
from random import randint

import pytest

from austin.events import AustinFrame
from austin.events import AustinMetadata
from austin.events import AustinMetrics
from austin.events import AustinSample
from austin.events import AustinTask
from austin.events import AustinTaskReport
from austin.format.collapsed_stack import main
from austin.format.mojo import UNKNOWN
from austin.format.mojo import MojoFrame
from austin.format.mojo import MojoFrameReference
from austin.format.mojo import MojoMetadata
from austin.format.mojo import MojoMetric
from austin.format.mojo import MojoMetricType
from austin.format.mojo import AsyncMojoStreamReader
from austin.format.mojo import MojoStack
from austin.format.mojo import MojoStreamReader
from austin.format.mojo import MojoStreamWriter
from austin.format.mojo import MojoString
from austin.format.mojo import MojoTaskRunning
from austin.format.mojo import MojoTaskStack
from austin.format.mojo import MojoTaskWaiter
from austin.format.mojo import to_varint

HERE = Path(__file__).parent
DATA = HERE.parent / "data"


@pytest.mark.parametrize("case", ["test", "mp", "repeat"])
def test_mojo_snapshot(case):
    input = (DATA / case).with_suffix(".mojo")
    output = Path(tempfile.NamedTemporaryFile().name).with_suffix(".austin")
    expected = (DATA / case).with_suffix(".austin")

    sys.argv = ["mojo2austin", str(input), str(output)]

    main()

    if not expected.exists():
        expected.write_text(output.read_text())
        raise AssertionError("Expected file does not exist. Created it.")

    assert expected.read_text()[:128] == output.read_text()[:128]


def test_mojo_varint():
    for _ in range(100_000):
        n = randint(int(-4e9), int(4e9))
        buffer = BytesIO()
        buffer.write(to_varint(n))
        buffer.seek(0)
        assert MojoStreamReader(buffer).read_int() == n


def test_mojo_column_info():
    with (DATA / "column.mojo").open("rb") as stream:
        frames = {
            _
            for _ in MojoStreamReader(stream).parse()
            if isinstance(_, MojoFrame) and _.filename.value == "/tmp/column.py"
        }
        assert frames == {
            MojoFrame(
                key=1289736945696,
                filename=MojoString(key=20271280, value="/tmp/column.py"),
                scope=MojoString(key=28930616, value="<module>"),
                line=15,
                line_end=18,
                column=5,
                column_end=2,
            ),
            MojoFrame(
                key=1293162643485,
                filename=MojoString(key=20271280, value="/tmp/column.py"),
                scope=MojoString(key=20364976, value="lazy"),
                line=5,
                line_end=5,
                column=9,
                column_end=19,
            ),
            MojoFrame(
                key=1293180469286,
                filename=MojoString(key=20271280, value="/tmp/column.py"),
                scope=MojoString(key=20357744, value="fib"),
                line=11,
                line_end=13,
                column=5,
                column_end=24,
            ),
            MojoFrame(
                key=1276044640259,
                filename=MojoString(key=20271280, value="/tmp/column.py"),
                scope=MojoString(key=28930552, value="<listcomp>"),
                line=15,
                line_end=18,
                column=5,
                column_end=2,
            ),
            MojoFrame(
                key=1289736945703,
                filename=MojoString(key=20271280, value="/tmp/column.py"),
                scope=MojoString(key=28930616, value="<module>"),
                line=20,
                line_end=20,
                column=1,
                column_end=9,
            ),
            MojoFrame(
                key=1293162643483,
                filename=MojoString(key=20271280, value="/tmp/column.py"),
                scope=MojoString(key=20364976, value="lazy"),
                line=5,
                line_end=5,
                column=9,
                column_end=19,
            ),
            MojoFrame(
                key=1276044640281,
                filename=MojoString(key=20271280, value="/tmp/column.py"),
                scope=MojoString(key=28930552, value="<listcomp>"),
                line=16,
                line_end=16,
                column=5,
                column_end=17,
            ),
        }


def test_mojo_data():
    input = (DATA / "test").with_suffix(".mojo")

    with input.open("rb") as stream:
        m = MojoStreamReader(stream)
        m.unwind()

        assert m.metadata == {
            "austin": "3.4.0",
            "duration": "1038089",
            "interval": "100",
            "mode": "wall",
        }

        n_samples = len(m.samples)
        assert n_samples == 13227


def test_mojo_writer():
    buffer = BytesIO()
    mojo_writer = MojoStreamWriter(buffer)

    mojo_writer.write(original_meta := AustinMetadata("mode", "wall"))
    for sample in (
        original_samples := [
            AustinSample(
                pid=42,
                iid=0,
                thread="0x7f45645646",
                metrics=AustinMetrics(time=1, memory=None),
                frames=None,
                gc=None,
                idle=None,
            ),
            AustinSample(
                pid=42,
                iid=0,
                thread="0x7f45645646",
                metrics=AustinMetrics(time=300, memory=None),
                frames=(
                    AustinFrame(
                        filename="foo_module.py",
                        function="foo",
                        line=10,
                        line_end=0,
                        column=0,
                        column_end=0,
                    ),
                ),
                gc=None,
                idle=None,
            ),
            AustinSample(
                pid=42,
                iid=0,
                thread="0x7f45645646",
                metrics=AustinMetrics(time=1000, memory=None),
                frames=(
                    AustinFrame(
                        filename="foo_module.py",
                        function="foo",
                        line=10,
                        line_end=0,
                        column=0,
                        column_end=0,
                    ),
                    AustinFrame(
                        filename="bar_sample.py",
                        function="bar",
                        line=20,
                        line_end=0,
                        column=0,
                        column_end=0,
                    ),
                ),
                gc=None,
                idle=None,
            ),
        ]
    ):
        mojo_writer.write(sample)

    buffer.seek(0)
    mojo_reader = MojoStreamReader(buffer)

    meta, *samples = mojo_reader

    assert meta == original_meta
    assert samples == original_samples


def _mojo_stream(*events: bytes) -> BytesIO:
    buffer = BytesIO()
    buffer.write(b"MOJ")
    buffer.write(to_varint(4))
    for event in events:
        buffer.write(event)
    buffer.seek(0)
    return buffer


def _mojo_task_frame(key: int) -> t.Tuple[MojoFrame, bytes]:
    """A minimal frame, referencing the predefined UNKNOWN string (key 1) for
    both filename and scope so the test doesn't need to register its own."""
    frame = MojoFrame(
        key=key,
        filename=UNKNOWN,
        scope=UNKNOWN,
        line=key,
        line_end=0,
        column=0,
        column_end=0,
    )
    return frame, frame.to_bytes() + MojoFrameReference(frame).to_bytes()


def test_mojo_tasks():
    """Two sibling tasks (worker-0, worker-1) on one event loop, each with a
    captured suspended coroutine-chain snapshot -- exercises the root tasks
    built from the accumulated MOJO_TASK_STACK/MOJO_TASK_WAITER events, owned
    by the enclosing sample's thread purely through wire position (no
    explicit loop/thread tag exists on either event).

    Order matters: task-scan events (TASK_STACK/TASK_WAITER) are emitted
    between the enclosing MOJO_STACK header and the enclosing sample's own
    frames/closing metric -- see py_proc.c's per-thread sampling order -- so
    this builds the wire in that exact sequence rather than nesting the task
    stacks "inside" the sample's own frame dump.
    """
    name = MojoString(key=5, value="worker-0")

    own_frame, own_frame_bytes = _mojo_task_frame(key=1)
    task_frame, task_frame_bytes = _mojo_task_frame(key=2)
    sibling_frame, sibling_frame_bytes = _mojo_task_frame(key=3)

    stream = _mojo_stream(
        MojoStack(pid=1, iid=0, tid="MainThread").to_bytes(),
        # Task scan: worker-1 (task_id=200) is awaited by worker-0
        # (task_id=100) -- an edge, then each task's own suspended chain.
        name.to_bytes(),
        MojoTaskWaiter(task_id=200, waiter_id=100).to_bytes(),
        MojoTaskStack(task_id=100, name_key=5, frame_count=1).to_bytes(),
        task_frame_bytes,
        MojoTaskStack(task_id=200, name_key=0, frame_count=1).to_bytes(),
        sibling_frame_bytes,
        # Enclosing sample's own frame and closing metric.
        own_frame_bytes,
        MojoMetric(MojoMetricType.TIME, 1000).to_bytes(),
    )

    reader = MojoStreamReader(stream)
    reader.unwind()

    assert len(reader.samples) == 1
    sample = reader.samples[0]

    # Both are first reports: no previous position, no time. As the stream's
    # last sample, it also carries the end-of-stream reports, with the time
    # both tasks spent at their position: that of the sample itself.
    first = {r.task_id: r for r in sample.task_reports if r.previous is None}
    end = {r.task_id: r for r in sample.task_reports if r.previous is not None}
    assert set(first) == set(end) == {100, 200}
    assert all(r.elapsed == 0 and not r.closing for r in first.values())
    assert all(r.elapsed == 1000 and r.frames == r.previous for r in end.values())

    (root,) = sample.tasks
    assert root.task_id == 100
    assert root.name == "worker-0"
    assert root.frames == (
        AustinFrame(
            filename="<unknown>",
            function="<unknown>",
            line=2,
            line_end=0,
            column=0,
            column_end=0,
        ),
    )

    (child,) = root.awaiting
    assert child.task_id == 200
    assert child.name is None
    assert child.awaiting == ()
    assert child.frames == (
        AustinFrame(
            filename="<unknown>",
            function="<unknown>",
            line=3,
            line_end=0,
            column=0,
            column_end=0,
        ),
    )


def test_mojo_tasks_writer_round_trip():
    """A sample carrying tasks survives MojoStreamWriter -> MojoStreamReader,
    including a task with more than one waiter -- the case write_tasks's own
    docstring warns needs edges for one task_id written contiguously.

    task_id itself is NOT expected to survive unchanged: resolve_task_id
    compresses it exactly like frame/string keys, since the original remote
    address carries no meaning of its own -- only the shape (identity,
    values, and waiter relationships) needs to come back out the same.
    """
    leaf = AustinTask(
        task_id=300,
        name="shared-leaf",
        frames=(
            AustinFrame(
                filename="shared.py",
                function="leaf",
                line=7,
                line_end=0,
                column=0,
                column_end=0,
            ),
        ),
    )
    root_a = AustinTask(
        task_id=100,
        name="worker-0",
        frames=(
            AustinFrame(
                filename="worker.py",
                function="run",
                line=1,
                line_end=0,
                column=0,
                column_end=0,
            ),
        ),
        awaiting=(leaf,),
    )
    root_b = AustinTask(
        task_id=200,
        name=None,
        frames=(
            AustinFrame(
                filename="worker.py",
                function="run",
                line=2,
                line_end=0,
                column=0,
                column_end=0,
            ),
        ),
        awaiting=(leaf,),
    )

    original_sample = AustinSample(
        pid=1,
        iid=0,
        thread="MainThread",
        metrics=AustinMetrics(time=1000, memory=None),
        frames=None,
        tasks=(root_a, root_b),
        task_reports=tuple(
            AustinTaskReport(
                task_id=task.task_id,
                name=task.name,
                frames=task.frames,
                previous=None,
                elapsed=elapsed,
            )
            for task, elapsed in ((leaf, 150), (root_a, 500), (root_b, 200))
        ),
    )

    buffer = BytesIO()
    writer = MojoStreamWriter(buffer)
    writer.write(original_sample)

    buffer.seek(0)
    (sample,) = MojoStreamReader(buffer)

    # task_id values are remapped by the writer's own compression, so the
    # roots are identified by name (their one stable, human-meaningful
    # property) rather than by their original -- now-gone -- task_id.
    tree_by_name = {task.name: task for task in sample.tasks}
    assert set(tree_by_name) == {"worker-0", None}
    worker_0 = tree_by_name["worker-0"]
    worker_1 = tree_by_name[None]

    # Task time isn't written: the reader works it out from the samples, so
    # every task gets a first report, and the sample's time at the end.
    first = {r.task_id: r.elapsed for r in sample.task_reports if r.previous is None}
    end = {r.task_id: r.elapsed for r in sample.task_reports if r.previous}
    assert len(first) == 3 and set(first.values()) == {0}
    assert set(end.values()) == {1000}

    # Confirms the ids actually changed (rather than this passing
    # vacuously) without hardcoding collection order: compression assigns
    # small, distinct, positive ids (0 stands for no task), nowhere near the
    # original 100/200/300 ids.
    assert worker_0.task_id != worker_1.task_id
    assert {worker_0.task_id, worker_1.task_id}.issubset(range(1, 4))

    # The shared leaf must show up as a child of BOTH roots, with both
    # waiters preserved -- this is the multi-waiter edge case. Both copies
    # refer to the very same (remapped) task_id, since it's the same task.
    (leaf_via_0,) = worker_0.awaiting
    (leaf_via_1,) = worker_1.awaiting
    assert leaf_via_0.task_id == leaf_via_1.task_id
    assert leaf_via_0.name == "shared-leaf"
    assert leaf_via_0.task_id in end


def test_mojo_task_closing_flush():
    """A closing flush (empty frames, just a final elapsed value) closes the
    task: its report carries its last position and final time, and the task
    is gone from every later sample. It lands in whichever thread's window
    happens to be current when eviction runs -- by then every thread for
    the cycle has already had its turn -- so it must not reattribute the
    task to that thread either."""
    task_frame, task_frame_bytes = _mojo_task_frame(key=1)
    t1_frame, t1_frame_bytes = _mojo_task_frame(key=2)
    t2_frame, t2_frame_bytes = _mojo_task_frame(key=3)
    t1_again_frame, t1_again_frame_bytes = _mojo_task_frame(key=4)
    name = MojoString(key=5, value="worker")

    stream = _mojo_stream(
        # T1's sample: task 100 gets a real capture, owned by T1.
        MojoStack(pid=1, iid=0, tid="T1").to_bytes(),
        name.to_bytes(),
        MojoTaskStack(task_id=100, name_key=5, frame_count=1).to_bytes(),
        task_frame_bytes,
        t1_frame_bytes,
        MojoMetric(MojoMetricType.TIME, 1000).to_bytes(),
        # T2's sample: task 100's closing flush lands here -- empty frames,
        # no name, arbitrary window.
        MojoStack(pid=1, iid=0, tid="T2").to_bytes(),
        MojoTaskStack(task_id=100, name_key=0, frame_count=0).to_bytes(),
        t2_frame_bytes,
        MojoMetric(MojoMetricType.TIME, 2000).to_bytes(),
        # T1's second sample: task 100 is gone.
        MojoStack(pid=1, iid=0, tid="T1").to_bytes(),
        t1_again_frame_bytes,
        MojoMetric(MojoMetricType.TIME, 3000).to_bytes(),
    )

    reader = MojoStreamReader(stream)
    reader.unwind()

    t1_first, t2_sample, t1_second = reader.samples
    assert len(t1_first.tasks) == 1

    (report,) = t2_sample.task_reports
    assert report.closing
    assert report.task_id == 100
    assert report.name == "worker"
    # The time of T1's sample, which task 100 spent at its position.
    assert report.elapsed == 1000
    assert report.previous == (
        AustinFrame(
            filename="<unknown>",
            function="<unknown>",
            line=1,
            line_end=0,
            column=0,
            column_end=0,
        ),
    )
    assert t2_sample.tasks == ()

    assert t1_second.tasks == ()
    assert t1_second.task_reports == ()


def _task_running_stream() -> bytes:
    """Two samples on one thread: the first while it runs task 100, the second
    while it runs no task."""
    task_frame, task_frame_bytes = _mojo_task_frame(key=1)
    own_frame, own_frame_bytes = _mojo_task_frame(key=2)

    return _mojo_stream(
        MojoStack(pid=1, iid=0, tid="MainThread").to_bytes(),
        MojoTaskStack(task_id=100, name_key=0, frame_count=1).to_bytes(),
        task_frame_bytes,
        MojoTaskRunning(task_id=100).to_bytes(),
        own_frame_bytes,
        MojoMetric(MojoMetricType.TIME, 1000).to_bytes(),
        MojoStack(pid=1, iid=0, tid="MainThread").to_bytes(),
        MojoFrameReference(own_frame).to_bytes(),
        MojoMetric(MojoMetricType.TIME, 2000).to_bytes(),
    ).getvalue()


def test_mojo_task_running():
    """MOJO_TASK_RUNNING sets the running task of the sample it appears in,
    and of that sample only."""
    reader = MojoStreamReader(BytesIO(_task_running_stream()))
    reader.unwind()

    running, idle = reader.samples
    assert running.running_task == 100
    assert running.metrics.time == 1000
    assert idle.running_task is None


@pytest.mark.asyncio
async def test_mojo_task_running_async():
    """Same as test_mojo_task_running, with the asynchronous reader."""
    stream = asyncio.StreamReader()
    stream.feed_data(_task_running_stream())
    stream.feed_eof()

    reader = AsyncMojoStreamReader(stream)
    samples = [e async for e in reader if isinstance(e, AustinSample)]

    running, idle = samples
    assert running.running_task == 100
    assert idle.running_task is None


def test_mojo_task_running_writer_round_trip():
    """A sample's running task survives MojoStreamWriter -> MojoStreamReader,
    under the same compressed id as the task it refers to."""
    frame = AustinFrame(
        filename="worker.py",
        function="work",
        line=1,
        line_end=0,
        column=0,
        column_end=0,
    )
    task = AustinTask(task_id=100, name="worker", frames=(frame,))

    buffer = BytesIO()
    writer = MojoStreamWriter(buffer)
    writer.write(AustinMetadata("mode", "wall"))
    writer.write(
        AustinSample(
            pid=1,
            iid=0,
            thread="MainThread",
            metrics=AustinMetrics(time=1000),
            frames=(frame,),
            tasks=(task,),
            running_task=100,
        )
    )
    buffer.seek(0)

    reader = MojoStreamReader(buffer)
    reader.unwind()

    (sample,) = reader.samples
    (read_task,) = sample.tasks
    assert sample.running_task == read_task.task_id
    assert sample.running_task != 0


def _task_report(task_id: int, frame_bytes: bytes) -> bytes:
    """A report of a task at a single frame (frame_bytes: its definition and
    reference)."""
    return (
        MojoTaskStack(task_id=task_id, name_key=0, frame_count=1).to_bytes()
        + frame_bytes
    )


def _austin_frame(frame: MojoFrame) -> AustinFrame:
    return AustinFrame(
        filename=frame.filename.value,
        function=frame.scope.value,
        line=frame.line,
        line_end=frame.line_end,
        column=frame.column,
        column_end=frame.column_end,
    )


def _sample_end(frame_bytes: bytes) -> bytes:
    return frame_bytes + MojoMetric(MojoMetricType.TIME, 1000).to_bytes()


def _roots(sample: AustinSample) -> t.Set[int]:
    return {task.task_id for task in sample.tasks}


def test_mojo_task_reports_counted_once():
    """A task report is attached to the sample it came with only, and its
    time is for the task's previous position, which it carries along: the
    time of the task's thread's samples while it was there."""
    first_frame, first_bytes = _mojo_task_frame(key=1)
    second_frame, second_bytes = _mojo_task_frame(key=2)
    own_frame, own_bytes = _mojo_task_frame(key=3)

    stream = _mojo_stream(
        MojoStack(pid=1, iid=0, tid="T").to_bytes(),
        _task_report(100, first_bytes),
        _sample_end(own_bytes),
        MojoStack(pid=1, iid=0, tid="T").to_bytes(),
        _sample_end(MojoFrameReference(own_frame).to_bytes()),
        MojoStack(pid=1, iid=0, tid="T").to_bytes(),
        _task_report(100, second_bytes),
        _sample_end(MojoFrameReference(own_frame).to_bytes()),
    )

    reader = MojoStreamReader(stream)
    reader.unwind()

    first, quiet, second = reader.samples
    assert [s.task_reports != () for s in reader.samples] == [True, False, True]
    assert _roots(quiet) == {100}

    # The two samples before it, at the first position.
    report, end = second.task_reports
    assert report.previous == (_austin_frame(first_frame),)
    assert report.frames == (_austin_frame(second_frame),)
    assert report.elapsed == 2000

    # Its own, at the second, carried by the end-of-stream report.
    assert end.previous == end.frames == report.frames
    assert end.elapsed == 1000

    assert sum(r.elapsed for s in reader.samples for r in s.task_reports) == 3000


def test_mojo_task_waiter_none():
    """A waiter of 0 means the task no longer has any waiter."""
    _, a_bytes = _mojo_task_frame(key=1)
    _, b_bytes = _mojo_task_frame(key=2)
    own_frame, own_bytes = _mojo_task_frame(key=3)

    stream = _mojo_stream(
        MojoStack(pid=1, iid=0, tid="T").to_bytes(),
        _task_report(100, a_bytes),
        _task_report(200, b_bytes),
        MojoTaskWaiter(task_id=200, waiter_id=100).to_bytes(),
        _sample_end(own_bytes),
        MojoStack(pid=1, iid=0, tid="T").to_bytes(),
        MojoTaskWaiter(task_id=200, waiter_id=0).to_bytes(),
        _sample_end(MojoFrameReference(own_frame).to_bytes()),
    )

    reader = MojoStreamReader(stream)
    reader.unwind()

    awaited, released = reader.samples
    assert _roots(awaited) == {100}
    assert _roots(released) == {100, 200}


def test_mojo_task_waiter_sets_dont_merge_across_samples():
    """Two waiter sets for the same task, one per sample, are two complete
    sets: the second replaces the first even with nothing in between."""
    _, a_bytes = _mojo_task_frame(key=1)
    _, b_bytes = _mojo_task_frame(key=2)
    _, c_bytes = _mojo_task_frame(key=3)
    own_frame, own_bytes = _mojo_task_frame(key=4)

    stream = _mojo_stream(
        MojoStack(pid=1, iid=0, tid="T").to_bytes(),
        _task_report(100, a_bytes),
        _task_report(200, b_bytes),
        _task_report(300, c_bytes),
        MojoTaskWaiter(task_id=300, waiter_id=100).to_bytes(),
        _sample_end(own_bytes),
        MojoStack(pid=1, iid=0, tid="T").to_bytes(),
        MojoTaskWaiter(task_id=300, waiter_id=200).to_bytes(),
        _sample_end(MojoFrameReference(own_frame).to_bytes()),
    )

    reader = MojoStreamReader(stream)
    reader.unwind()

    root_a, root_b = sorted(reader.samples[-1].tasks, key=lambda t: t.task_id)
    assert root_a.task_id == 100 and root_a.awaiting == ()
    assert [c.task_id for c in root_b.awaiting] == [300]


def test_mojo_task_unknown_waiter():
    """A task awaited by a waiter that was never reported still shows up."""
    _, a_bytes = _mojo_task_frame(key=1)
    _, own_bytes = _mojo_task_frame(key=2)

    stream = _mojo_stream(
        MojoStack(pid=1, iid=0, tid="T").to_bytes(),
        _task_report(100, a_bytes),
        MojoTaskWaiter(task_id=100, waiter_id=999).to_bytes(),
        _sample_end(own_bytes),
    )

    reader = MojoStreamReader(stream)
    reader.unwind()

    assert _roots(reader.samples[0]) == {100}


def test_mojo_task_closed_waiter():
    """When a waiter closes, the task it awaited is no longer under it."""
    _, a_bytes = _mojo_task_frame(key=1)
    _, b_bytes = _mojo_task_frame(key=2)
    own_frame, own_bytes = _mojo_task_frame(key=3)

    stream = _mojo_stream(
        MojoStack(pid=1, iid=0, tid="T").to_bytes(),
        _task_report(100, a_bytes),
        _task_report(200, b_bytes),
        MojoTaskWaiter(task_id=200, waiter_id=100).to_bytes(),
        _sample_end(own_bytes),
        MojoStack(pid=1, iid=0, tid="T").to_bytes(),
        MojoTaskStack(task_id=100, name_key=0, frame_count=0).to_bytes(),
        _sample_end(MojoFrameReference(own_frame).to_bytes()),
    )

    reader = MojoStreamReader(stream)
    reader.unwind()

    assert _roots(reader.samples[-1]) == {200}


def test_mojo_task_waiter_none_writer_round_trip():
    """A task losing its last waiter survives MojoStreamWriter ->
    MojoStreamReader."""
    frame = AustinFrame(
        filename="t.py", function="f", line=1, line_end=0, column=0, column_end=0
    )
    child = AustinTask(task_id=200, name="child", frames=(frame,))
    parent = AustinTask(task_id=100, name="parent", frames=(frame,), awaiting=(child,))

    def sample(tasks: t.Tuple[AustinTask, ...]) -> AustinSample:
        return AustinSample(
            pid=1,
            iid=0,
            thread="T",
            metrics=AustinMetrics(time=1000),
            frames=(frame,),
            tasks=tasks,
        )

    buffer = BytesIO()
    writer = MojoStreamWriter(buffer)
    writer.write(AustinMetadata("mode", "wall"))
    writer.write(sample((parent,)))
    writer.write(sample((AustinTask(100, "parent", (frame,)), child)))
    buffer.seek(0)

    reader = MojoStreamReader(buffer)
    reader.unwind()

    awaited, released = reader.samples
    assert {t.name for t in awaited.tasks} == {"parent"}
    assert {t.name for t in released.tasks} == {"parent", "child"}


def _derivation_stream(mode: str) -> BytesIO:
    """Tasks 100 and 200 on thread T, task 300 on thread U. T runs task 100 in
    its second sample. Every sample takes 1000."""
    _, a_bytes = _mojo_task_frame(key=1)
    _, b_bytes = _mojo_task_frame(key=2)
    _, c_bytes = _mojo_task_frame(key=3)
    own_frame, own_bytes = _mojo_task_frame(key=4)
    own = MojoFrameReference(own_frame).to_bytes()

    return _mojo_stream(
        MojoMetadata("mode", mode).to_bytes(),
        MojoStack(pid=1, iid=0, tid="T").to_bytes(),
        _task_report(100, a_bytes),
        _task_report(200, b_bytes),
        _sample_end(own_bytes),
        MojoStack(pid=1, iid=0, tid="U").to_bytes(),
        _task_report(300, c_bytes),
        _sample_end(own),
        MojoStack(pid=1, iid=0, tid="T").to_bytes(),
        MojoTaskRunning(task_id=100).to_bytes(),
        _sample_end(own),
        MojoStack(pid=1, iid=0, tid="U").to_bytes(),
        _sample_end(own),
    )


def test_mojo_task_time_from_samples():
    """A task accrues its own thread's sample time while it isn't running,
    and only that, until it is reported again (here, at the end)."""
    reader = MojoStreamReader(_derivation_stream("wall"))
    reader.unwind()

    end = {r.task_id: r.elapsed for r in reader.samples[-1].task_reports}

    # T's two samples, but the one it was running at; T's two samples; U's
    # two samples.
    assert end == {100: 1000, 200: 2000, 300: 2000}


def test_mojo_task_time_cpu_mode():
    """In CPU mode, a task that isn't running uses no CPU: no await time."""
    reader = MojoStreamReader(_derivation_stream("cpu"))
    reader.unwind()

    reports = [r for s in reader.samples for r in s.task_reports]
    assert reports and all(r.elapsed == 0 for r in reports)
    assert all(r.previous is None for r in reports)
