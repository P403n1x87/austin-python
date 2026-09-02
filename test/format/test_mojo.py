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
from austin.format.collapsed_stack import main
from austin.format.mojo import UNKNOWN
from austin.format.mojo import MojoFrame
from austin.format.mojo import MojoFrameReference
from austin.format.mojo import MojoMetric
from austin.format.mojo import MojoMetricType
from austin.format.mojo import MojoStack
from austin.format.mojo import MojoStreamReader
from austin.format.mojo import MojoStreamWriter
from austin.format.mojo import MojoString
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
        MojoTaskStack(task_id=100, name_key=5).to_bytes(),
        task_frame_bytes,
        MojoMetric(MojoMetricType.TIME, 500).to_bytes(),
        MojoTaskStack(task_id=200, name_key=0).to_bytes(),
        sibling_frame_bytes,
        MojoMetric(MojoMetricType.TIME, 200).to_bytes(),
        # Enclosing sample's own frame and closing metric.
        own_frame_bytes,
        MojoMetric(MojoMetricType.TIME, 1000).to_bytes(),
    )

    reader = MojoStreamReader(stream)
    reader.unwind()

    assert len(reader.samples) == 1
    sample = reader.samples[0]

    (root,) = sample.tasks
    assert root.task_id == 100
    assert root.name == "worker-0"
    assert root.elapsed == 500
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
    assert child.elapsed == 200
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
        elapsed=150,
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
        elapsed=500,
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
        elapsed=200,
        awaiting=(leaf,),
    )

    original_sample = AustinSample(
        pid=1,
        iid=0,
        thread="MainThread",
        metrics=AustinMetrics(time=1000, memory=None),
        frames=None,
        tasks=(root_a, root_b),
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
    assert worker_0.elapsed == 500
    assert worker_1.elapsed == 200

    # Confirms the ids actually changed (rather than this passing
    # vacuously) without hardcoding collection order: compression assigns
    # small, distinct, non-negative ids, nowhere near the original
    # 100/200/300 remote addresses.
    assert worker_0.task_id != worker_1.task_id
    assert {worker_0.task_id, worker_1.task_id}.issubset(range(3))

    # The shared leaf must show up as a child of BOTH roots, with both
    # waiters preserved -- this is the multi-waiter edge case. Both copies
    # refer to the very same (remapped) task_id, since it's the same task.
    (leaf_via_0,) = worker_0.awaiting
    (leaf_via_1,) = worker_1.awaiting
    assert leaf_via_0.task_id == leaf_via_1.task_id
    assert leaf_via_0.name == "shared-leaf"
    assert leaf_via_0.elapsed == 150


def test_mojo_task_stack_eviction_flush_keeps_frames_and_owner():
    """A closing flush (empty frames, just a final elapsed value) for a task
    that's about to be evicted must not wipe its last real frames, nor
    reattribute it to whichever thread happens to be current when eviction
    runs -- by then every thread for the cycle has already had its turn, so
    that thread is arbitrary, not the task's actual owner."""
    task_frame, task_frame_bytes = _mojo_task_frame(key=1)
    t1_frame, t1_frame_bytes = _mojo_task_frame(key=2)
    t2_frame, t2_frame_bytes = _mojo_task_frame(key=3)
    t1_again_frame, t1_again_frame_bytes = _mojo_task_frame(key=4)

    stream = _mojo_stream(
        # T1's sample: task 100 gets a real capture, owned by T1.
        MojoStack(pid=1, iid=0, tid="T1").to_bytes(),
        MojoTaskStack(task_id=100, name_key=0).to_bytes(),
        task_frame_bytes,
        MojoMetric(MojoMetricType.TIME, 500).to_bytes(),
        t1_frame_bytes,
        MojoMetric(MojoMetricType.TIME, 1000).to_bytes(),
        # T2's sample: task 100's eviction/closing flush lands here --
        # empty frames, arbitrary window.
        MojoStack(pid=1, iid=0, tid="T2").to_bytes(),
        MojoTaskStack(task_id=100, name_key=0).to_bytes(),
        MojoMetric(MojoMetricType.TIME, 999).to_bytes(),
        t2_frame_bytes,
        MojoMetric(MojoMetricType.TIME, 2000).to_bytes(),
        # T1's second sample: task 100 wasn't re-captured, but should still
        # show up in T1's tree via best-known state.
        MojoStack(pid=1, iid=0, tid="T1").to_bytes(),
        t1_again_frame_bytes,
        MojoMetric(MojoMetricType.TIME, 3000).to_bytes(),
    )

    reader = MojoStreamReader(stream)
    reader.unwind()

    assert len(reader.samples) == 3
    t1_second_sample = reader.samples[2]
    assert t1_second_sample.thread == "T1"

    (task,) = t1_second_sample.tasks
    assert task.task_id == 100
    assert task.elapsed == 999
    assert task.frames == (
        AustinFrame(
            filename="<unknown>",
            function="<unknown>",
            line=1,
            line_end=0,
            column=0,
            column_end=0,
        ),
    )

    # T2 never actually owned task 100 -- the closing flush must not have
    # reattributed it.
    t2_sample = reader.samples[1]
    assert t2_sample.tasks == ()
