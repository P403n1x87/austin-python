import json
import typing as t

import pytest

from austin.events import AustinFrame
from austin.events import AustinMetadata
from austin.events import AustinMetrics
from austin.events import AustinSample
from austin.events import AustinTask
from austin.query import ALL
from austin.query import ROOT
from austin.query import SELF
from austin.query import Location
from austin.query import NoMatchError
from austin.query import PathShortener
from austin.query import ProfileQuery
from austin.query import matcher
from austin.query import task_matcher
from austin.stats import AustinStatsType


def frames(stack: str) -> t.Tuple[AustinFrame, ...]:
    """Parse a ';'-separated list of file:function:line frames."""
    result = []
    for frame in stack.split(";") if stack else ():
        filename, function, line = frame.rsplit(":", 2)
        result.append(AustinFrame(filename, function, int(line)))
    return tuple(result)


def sample(
    stack: str,
    time: t.Optional[int] = None,
    memory: t.Optional[int] = None,
    thread: str = "t1",
    pid: int = 1,
    idle: t.Optional[bool] = None,
    gc: t.Optional[bool] = None,
) -> AustinSample:
    return AustinSample(
        pid=pid,
        iid=0,
        thread=thread,
        metrics=AustinMetrics(time=time, memory=memory),
        frames=frames(stack),
        idle=idle,
        gc=gc,
    )


def wall(*samples: AustinSample) -> ProfileQuery:
    return ProfileQuery([AustinMetadata("mode", "wall"), *samples])


F = Location("a.py", "f")
G = Location("a.py", "g")
H = Location("b.py", "h")


@pytest.fixture
def recursive() -> ProfileQuery:
    return wall(
        sample("a.py:f:1;a.py:g:2;a.py:f:3", 10),
        sample("a.py:f:1", 5),
        sample("a.py:g:2", 3),
    )


def test_top_is_recursion_safe(recursive):
    top = recursive.top()

    assert top.profile_total == 18
    assert top.profile_samples == 3

    entries = {e.location: e for e in top}
    assert entries[F].own == 15
    assert entries[F].total == 15  # not 25
    assert entries[F].total_samples == 2
    assert entries[G].own == 3
    assert entries[G].total == 13
    assert entries[G].own_samples == 1

    assert [e.location for e in top] == [F, G]
    assert [e.location for e in recursive.top(by="total")] == [F, G]
    assert len(recursive.top(1)) == 1


def test_top_lines(recursive):
    entries = {e.location: e for e in recursive.top(lines=True)}

    assert entries[Location("a.py", "f", 1)].total == 15
    assert entries[Location("a.py", "f", 3)].own == 10
    assert entries[Location("a.py", "g", 2)].total == 13


def test_top_invalid_sort_key(recursive):
    with pytest.raises(ValueError):
        recursive.top(by="samples")


def test_callers(recursive):
    callers = recursive.callers("f")

    assert callers.matched == (F,)
    assert callers.own == 15
    assert callers.total == 15
    assert {e.location: e.value for e in callers} == {ROOT: 15, G: 10}
    assert callers[0].location == ROOT
    assert callers[0].share == 100
    assert round(callers[1].share, 1) == 66.7


def test_callers_count_each_stack_once():
    q = wall(sample("a.py:f:1;a.py:g:2;a.py:f:3;a.py:g:2;a.py:f:3", 7))

    assert {e.location: e.value for e in q.callers("f")} == {ROOT: 7, G: 7}
    assert {e.location: e.value for e in q.callees("f")} == {G: 7, SELF: 7}


def test_callees(recursive):
    callees = recursive.callees("g")

    assert callees.total == 13
    assert {e.location: e.value for e in callees} == {F: 10, SELF: 3}
    assert sum(e.value for e in callees) == callees.total


def test_neighbours_aggregate_matches(recursive):
    callers = recursive.callers("re:a\\.py:(f|g):")

    assert callers.matched == (F, G)
    assert callers.total == 18
    assert {e.location: e.value for e in callers} == {ROOT: 18, F: 10, G: 10}


def test_neighbours_no_match(recursive):
    with pytest.raises(NoMatchError, match="did you mean one of: f"):
        recursive.callers("ff")

    with pytest.raises(NoMatchError):
        recursive.callees("nope")


def test_lines():
    q = wall(
        sample("a.py:f:1;b.py:h:7", 10),
        sample("a.py:f:2", 4),
        sample("a.py:f:1", 1),
    )
    result = q.lines("f")

    assert result.matched == (F,)
    assert [(e.location.line, e.own, e.total) for e in result] == [
        (1, 1, 11),
        (2, 4, 4),
    ]

    with pytest.raises(NoMatchError):
        q.lines("g")


def test_find(recursive):
    result = recursive.find("a.py")

    assert result.matched == (F, G)
    assert [e.location for e in result] == [F, G]
    assert not recursive.find("b.py").entries


def test_stacks():
    q = wall(
        sample("a.py:f:1;a.py:g:2", 10, thread="t1"),
        sample("a.py:f:1;a.py:g:3", 5, thread="t2"),
        sample("a.py:f:1", 3, thread="t1"),
        sample("", 1, thread="t2"),
    )

    stacks = q.stacks()
    assert stacks.count == 3
    assert [(s.frames, s.value, s.samples) for s in stacks] == [
        ((F, G), 15, 2),
        ((F,), 3, 1),
        ((), 1, 1),
    ]
    assert stacks[0].thread is None

    per_thread = q.stacks(per_thread=True, lines=True)
    assert per_thread.count == 4
    assert per_thread[0].frames == (Location("a.py", "f", 1), Location("a.py", "g", 2))
    assert (per_thread[0].pid, per_thread[0].thread) == (1, "t1")

    assert len(q.stacks(1)) == 1


def test_tree():
    q = wall(
        sample("a.py:f:1;a.py:g:2;b.py:h:3", 90),
        sample("a.py:f:1;a.py:g:2;a.py:f:4;a.py:g:2", 9),
        sample("b.py:h:3", 1),
    )

    tree = q.tree(min_pct=0)
    assert tree.root.location == ALL
    assert tree.root.total == 100
    f, h = tree.root.children
    assert (f.location, f.total, f.pct) == (F, 99, 99)
    assert (h.location, h.own) == (H, 1)
    assert [c.location for c in f.children[0].children] == [H, F]

    pruned = q.tree(min_pct=10)
    assert [c.location for c in pruned.root.children] == [F]
    assert [c.location for c in pruned.root.children[0].children[0].children] == [H]

    shallow = q.tree(max_depth=1, min_pct=0)
    assert [c.location for c in shallow.root.children] == [F, H]
    assert all(not c.children for c in shallow.root.children)


def test_tree_rooted_at_selector():
    q = wall(
        sample("a.py:f:1;a.py:g:2;b.py:h:3", 90),
        sample("a.py:f:1;a.py:g:2;a.py:f:4;a.py:g:2", 9),
        sample("b.py:h:3", 1),
    )

    tree = q.tree("g", min_pct=0)
    assert tree.matched == (G,)
    assert tree.root.location == G
    assert tree.root.total == 99  # Outermost occurrences only
    assert [(c.location, c.total) for c in tree.root.children] == [(H, 90), (F, 9)]

    with pytest.raises(NoMatchError):
        q.tree("nope")


def test_filter():
    q = wall(
        sample("a.py:f:1;a.py:g:2", 10, thread="t1", pid=1),
        sample("a.py:f:1", 6, thread="t2", pid=1),
        sample("b.py:h:3", 4, thread="t1", pid=2),
    )

    t1 = q.filter(thread="t1")
    assert t1.top().profile_total == 14
    assert {e.location: e.total_pct for e in t1.top()}[H] == pytest.approx(400 / 14)

    assert q.filter(pid=2).top().profile_total == 4
    assert q.filter(contains="g").top().profile_total == 10
    assert q.filter(where=lambda s: s.metrics.time > 5).top().profile_total == 16
    assert q.filter(thread="t1", pid=1).top().profile_total == 10
    assert not q.filter(thread="t3").samples

    # Filtering does not affect the original profile
    assert q.top().profile_total == 20


def test_filter_flags():
    q = ProfileQuery(
        [
            AustinMetadata("mode", "full"),
            sample("a.py:f:1", 10, 0, idle=True, gc=False),
            sample("a.py:f:1", 5, 0, idle=False, gc=True),
        ]
    )

    assert q.filter(idle=True).top().profile_total == 10
    assert q.filter(idle=False).top().profile_total == 5
    assert q.filter(gc=True).top().profile_total == 5


def test_full_mode_metrics():
    q = ProfileQuery(
        [
            AustinMetadata("mode", "full"),
            sample("a.py:f:1", 100, 64, idle=False),
            sample("a.py:f:1;a.py:g:2", 900, -16, idle=True),
        ]
    )

    assert q.metrics == tuple(AustinStatsType)
    assert q.metric() is AustinStatsType.WALL
    assert q.top().profile_total == 1000
    assert q.top(metric="cpu").profile_total == 100
    assert q.top(metric="memory").profile_total == 64
    assert q.top(metric=AustinStatsType.MEMORY_DEALLOC).profile_total == 16

    with pytest.raises(NoMatchError):
        # g only appears in an idle sample, which has no CPU time
        q.callers("g", metric="cpu")


def test_metric_validation():
    q = wall(sample("a.py:f:1", 1))

    assert q.metric("WALL") is AustinStatsType.WALL

    with pytest.raises(ValueError, match="Unknown metric"):
        q.metric("bogus")

    with pytest.raises(ValueError, match="not available in wall mode"):
        q.top(metric="cpu")


@pytest.mark.parametrize(
    "samples,mode",
    [
        ([sample("a.py:f:1", 1)], "wall"),
        ([sample("a.py:f:1", memory=1)], "memory"),
        ([sample("a.py:f:1", 1, 1)], "full"),
    ],
)
def test_mode_inference(samples, mode):
    assert ProfileQuery(samples).mode == mode


def test_memory_mode_default_metric():
    q = ProfileQuery([AustinMetadata("mode", "memory"), sample("a.py:f:1", memory=8)])

    assert q.metric() is AustinStatsType.MEMORY_ALLOC
    assert "8B" in str(q.top())


@pytest.mark.parametrize(
    "selector,frame,expected",
    [
        ("f", AustinFrame("a.py", "f", 1), True),
        ("f", AustinFrame("a.py", "Cls.f", 1), True),
        ("f", AustinFrame("a.py", "ff", 1), False),
        ("Cls.f", AustinFrame("a.py", "Cls.f", 1), True),
        ("a.py:f", AustinFrame("/src/a.py", "f", 1), True),
        ("a.py:f", AustinFrame("/src/xa.py", "f", 1), False),
        ("src/a.py:f", AustinFrame("/src/a.py", "f", 1), True),
        ("a.py:f:1", AustinFrame("a.py", "f", 1), True),
        ("a.py:f:2", AustinFrame("a.py", "f", 1), False),
        ("a.py", AustinFrame("/src/a.py", "f", 1), True),
        ("a.py:7", AustinFrame("/src/a.py", "f", 7), True),
        ("C:\\src\\a.py", AustinFrame("C:\\src\\a.py", "f", 7), True),
        ("a.py:f", AustinFrame("C:\\src\\a.py", "f", 7), True),
        (
            "<frozen importlib._bootstrap>:_find_and_load",
            AustinFrame("<frozen importlib._bootstrap>", "_find_and_load", 1),
            True,
        ),
        ("re:^/src/.*:f:", AustinFrame("/src/a.py", "f", 1), True),
        ("re:^/lib/", AustinFrame("/src/a.py", "f", 1), False),
        (Location("a.py", "f"), AustinFrame("a.py", "f", 1), True),
        (Location("a.py", "f", 2), AustinFrame("a.py", "f", 1), False),
        (AustinFrame("a.py", "f", 1, column=4), AustinFrame("a.py", "f", 1), True),
        (lambda f: f.line > 5, AustinFrame("a.py", "f", 1), False),
    ],
)
def test_matcher(selector, frame, expected):
    assert matcher(selector)(frame) is expected


def test_summary():
    q = ProfileQuery(
        [
            AustinMetadata("mode", "full"),
            AustinMetadata("interval", "100"),
            sample("a.py:f:1", 30, 0, thread="t1", idle=False),
            sample("a.py:f:1", 10, 0, thread="t2", idle=True),
        ]
    )
    summary = q.summary()

    assert summary.mode == "full"
    assert summary.metric is AustinStatsType.WALL
    assert {m.metric: m.total for m in summary.metrics}[AustinStatsType.CPU] == 30
    assert [(th.thread, th.pct) for th in summary.threads] == [("t1", 75), ("t2", 25)]

    text = str(summary)
    assert "mode: full" in text
    assert "interval: 100" in text


def test_render(recursive):
    assert "a.py:f" in str(recursive.top())
    assert "callers of a.py:f" in str(recursive.callers("f"))
    assert "matched: a.py:g" in str(recursive.callees("re:a.py"))
    assert "<no frames>" in str(wall(sample("", 1)).stacks())
    assert "  a.py:g" in str(recursive.tree(min_pct=0))
    assert "18µs" in str(recursive.top())


def test_to_dict_is_json_serializable(recursive):
    for result in (
        recursive.summary(),
        recursive.top(),
        recursive.find("f"),
        recursive.lines("f"),
        recursive.stacks(per_thread=True),
        recursive.callers("f"),
        recursive.callees("f"),
        recursive.tree(),
        recursive.tree("g"),
    ):
        json.dumps(result.to_dict())

    data = recursive.callers("f").to_dict()
    assert data["metric"] == "wall"
    assert data["matched"] == ["a.py:f"]
    assert data["entries"][0]["location"] == "<root>"

    tree = recursive.tree(min_pct=0).to_dict()
    assert tree["root"]["children"][0]["location"] == "a.py:f"


def test_deep_stacks():
    depth = 5000
    stack = ";".join(f"a.py:f{i % 3}:{i}" for i in range(depth))
    q = wall(sample(stack, 1))

    assert q.top()[0].total == 1
    assert q.callers("f0").total == 1
    assert len(q.stacks()[0].frames) == depth
    tree = q.tree()
    tree.to_dict()
    str(tree)


@pytest.mark.parametrize("name", ["test.mojo", "test.austin"])
def test_from_file(datapath, name):
    q = ProfileQuery.from_file(datapath / name)

    assert q.mode == "wall"
    assert q.top().profile_total == 2044073
    assert q.stacks().count > 0


@pytest.mark.parametrize(
    "filename,metadata,expected",
    [
        # Built-in roots, without metadata
        ("/py/lib/python3.13/threading.py", {}, "threading.py"),
        ("/py/lib/python3.14t/asyncio/tasks.py", {}, "asyncio/tasks.py"),
        ("/v/lib/python3.13/site-packages/requests/api.py", {}, "requests/api.py"),
        ("/usr/lib/python3/dist-packages/yaml/main.py", {}, "yaml/main.py"),
        ("C:\\Python313\\Lib\\threading.py", {}, "threading.py"),
        ("C:\\Python313\\Lib\\site-packages\\req\\api.py", {}, "req\\api.py"),
        ("/proj/app/db.py", {}, "/proj/app/db.py"),
        ("/usr/lib/python3.13/libfoo.so", {}, "/usr/lib/python3.13/libfoo.so"),
        ("<frozen importlib._bootstrap>", {}, "<frozen importlib._bootstrap>"),
        # Metadata roots
        ("/proj/app/db.py", {"cwd": "/proj"}, "app/db.py"),
        ("/proj/app/db.py", {"cwd": "/proj/"}, "app/db.py"),
        ("/project/db.py", {"cwd": "/proj"}, "/project/db.py"),
        ("/proj/lib.so", {"cwd": "/proj"}, "lib.so"),
        ("/any/db.py", {"cwd": "/"}, "/any/db.py"),
        (
            "/proj/.venv/lib/python3.13/site-packages/req/api.py",
            {"cwd": "/proj", "venv": "/proj/.venv"},
            "req/api.py",
        ),
        (
            "/proj/.venv/bin/tool.py",
            {"cwd": "/proj", "venv": "/proj/.venv"},
            "bin/tool.py",
        ),
        (
            "/proj/src/pkg/mod.py",
            {"cwd": "/proj", "pythonpath": "/opt:/proj/src"},
            "pkg/mod.py",
        ),
        ("/proj/src/pkg/mod.py", {"cwd": "/proj", "pythonpath": "src"}, "pkg/mod.py"),
        ("/proj/src/pkg/mod.py", {"pythonpath": "src"}, "/proj/src/pkg/mod.py"),
        (
            "C:\\proj\\src\\pkg\\mod.py",
            {"cwd": "C:\\proj", "pythonpath": "C:\\opt;src"},
            "pkg\\mod.py",
        ),
    ],
)
def test_path_shortener(filename, metadata, expected):
    assert PathShortener([filename], metadata)(filename) == expected


def test_path_shortener_keeps_paths_unique():
    filenames = [
        "/proj/app/util.py",
        "/v/site-packages/lib/app/util.py",
        "/a/site-packages/x.py",
        "/b/site-packages/x.py",
        "/proj/main.py",
    ]
    paths = PathShortener(filenames, {"cwd": "/proj"})

    assert [paths(f) for f in filenames] == [
        "proj/app/util.py",
        "lib/app/util.py",
        "a/site-packages/x.py",
        "b/site-packages/x.py",
        "main.py",
    ]
    assert paths("/unknown/file.py") == "/unknown/file.py"

    # Every shortened path selects exactly its own file
    for f in filenames:
        frame = AustinFrame(f, "fn", 1)
        assert [
            g for g in filenames if matcher(f"{paths(f)}:fn")(AustinFrame(g, "fn", 1))
        ] == [f], frame


def test_short_paths_in_results():
    q = ProfileQuery(
        [
            AustinMetadata("mode", "wall"),
            AustinMetadata("cwd", "/proj"),
            sample("/proj/app/main.py:main:1;/py/lib/python3.13/threading.py:run:2", 5),
            sample("/proj/app/main.py:main:1", 1, thread="t2"),
        ]
    )

    text = str(q.top())
    assert "app/main.py:main" in text
    assert "threading.py:run" in text
    assert "/proj" not in text
    assert "/py/lib" not in text

    assert "  app/main.py:main" in str(q.stacks())
    assert "callers of threading.py:run" in str(q.callers("threading.py:run"))
    assert "  app/main.py:main" in str(q.tree(min_pct=0))

    # Full paths in the data
    entries = q.top(by="total").to_dict()["entries"]
    assert entries[0]["location"] == "/proj/app/main.py:main"
    assert "paths" not in q.top().to_dict()

    # Filtered profiles keep the paths of the full profile
    assert q.filter(thread="t2").paths is q.paths

    full = ProfileQuery(q.samples, short_paths=False)
    assert "/proj/app/main.py:main" in str(full.top())


# ---- asyncio tasks ----


def task(
    task_id: int,
    stack: str,
    *awaiting: AustinTask,
    name: t.Optional[str] = None,
) -> AustinTask:
    return AustinTask(
        task_id=task_id,
        name=name if name is not None else f"task-{task_id}",
        frames=frames(stack),
        awaiting=awaiting,
    )


def task_sample(
    stack: str,
    time: int,
    tasks: t.Tuple[AustinTask, ...],
    running: t.Optional[int] = None,
    thread: str = "t1",
    idle: t.Optional[bool] = None,
) -> AustinSample:
    return AustinSample(
        pid=1,
        iid=0,
        thread=thread,
        metrics=AustinMetrics(time=time),
        frames=frames(stack),
        idle=idle,
        tasks=tasks,
        running_task=running,
    )


LOOP = "main.py:main:1;events.py:_run:2"


def test_running_task_frames_are_stitched_to_the_thread_stack():
    child = task(2, "w.py:worker:5;w.py:burst:6")
    root = task(1, "m.py:main:3", child)
    q = wall(
        task_sample(LOOP, 10, (root,), running=2),
        task_sample(LOOP, 5, (root,)),
    )

    running, suspended = q.stacks()
    assert [str(_) for _ in running.frames] == [
        "main.py:main",
        "events.py:_run",
        "w.py:worker",
        "w.py:burst",
    ]
    assert running.value == 10
    assert [str(_) for _ in suspended.frames] == ["main.py:main", "events.py:_run"]
    assert q.top()[0].location == Location("w.py", "burst")
    assert q.callers("burst")[0].location == Location("w.py", "worker")


def test_running_task_without_a_known_position_keeps_the_thread_stack():
    q = wall(task_sample(LOOP, 10, (task(1, "m.py:main:3"),), running=7))

    (stack,) = q.stacks()
    assert [str(_) for _ in stack.frames] == ["main.py:main", "events.py:_run"]


def test_tasks_wall_total_is_time_alive():
    child = task(2, "w.py:worker:5")
    root = task(1, "m.py:main:3", child)
    q = wall(
        task_sample(LOOP, 10, (task(1, "m.py:main:3"),), running=1),
        task_sample(LOOP, 20, (root,), running=2),
        task_sample(LOOP, 30, (root,)),
        task_sample(LOOP, 40, (task(1, "m.py:main:3"),), running=1),
    )

    (main,) = q.tasks()
    assert (main.task_id, main.name) == (1, "task-1")
    assert (main.running, main.awaiting, main.total) == (50, 50, 100)
    assert main.pct == 100.0
    (worker,) = main.children
    assert (worker.running, worker.awaiting, worker.total) == (20, 30, 50)


def test_tasks_cpu_total_adds_awaited_tasks():
    leaf = task(3, "l.py:leaf:1")
    mid = task(2, "w.py:worker:5", leaf)
    root = task(1, "m.py:main:3", mid)
    q = ProfileQuery(
        [
            AustinMetadata("mode", "cpu"),
            task_sample(LOOP, 10, (root,), running=1),
            task_sample(LOOP, 20, (root,), running=2),
            task_sample(LOOP, 30, (root,), running=3),
        ]
    )

    (main,) = q.tasks()
    assert (main.running, main.awaiting, main.total) == (10, 0, 60)
    (worker,) = main.children
    assert (worker.running, worker.total) == (20, 50)
    (leaf_node,) = worker.children
    assert (leaf_node.running, leaf_node.total) == (30, 30)


def test_tasks_are_grouped_by_thread_and_sorted():
    q = wall(
        task_sample(LOOP, 10, (task(1, "a.py:a:1"), task(2, "b.py:b:1")), running=2),
        task_sample(LOOP, 10, (task(2, "b.py:b:1"),), running=2),
        task_sample(LOOP, 5, (task(3, "c.py:c:1"),), thread="t2"),
    )

    result = q.tasks()
    assert [(r.thread, r.task_id) for r in result] == [("t1", 2), ("t1", 1), ("t2", 3)]
    assert [r.total for r in result] == [20, 10, 5]


def test_tasks_survive_a_waiter_cycle():
    a = AustinTask(1, "a", frames("a.py:a:1"), ())
    b = AustinTask(2, "b", frames("b.py:b:1"), (a,))
    a_awaits_b = AustinTask(1, "a", frames("a.py:a:1"), (b,))
    q = wall(task_sample(LOOP, 10, (a_awaits_b,)))

    result = q.tasks()
    assert sorted(n.task_id for r in result for n in [r, *r.children]) == [1, 2]


def test_filter_by_running_task():
    child = task(2, "w.py:worker:5;w.py:burst:6", name="worker")
    root = task(1, "m.py:main:3", child, name="main")
    q = wall(
        task_sample(LOOP, 10, (root,), running=2),
        task_sample(LOOP, 20, (root,), running=1),
        task_sample(LOOP, 30, (root,)),
    )

    assert q.filter(task="worker").top()[0].location == Location("w.py", "burst")
    assert q.filter(task=2).summary().profile_total == 10
    assert q.filter(task="re:^ma").summary().profile_total == 20
    assert q.filter(task=lambda t: t.task_id == 1).summary().profile_total == 20
    with pytest.raises(NoMatchError):
        q.filter(task=lambda t: t.task_id > 5)


def test_task_matcher():
    worker = AustinTask(2, "worker-0", (), ())
    assert task_matcher(2)(worker)
    assert task_matcher("worker-0")(worker)
    assert not task_matcher("worker")(worker)
    assert task_matcher("re:worker")(worker)
    assert not task_matcher("re:x")(AustinTask(3, None, (), ()))


def test_tasks_render_and_to_dict():
    child = task(2, "w.py:worker:5")
    q = wall(task_sample(LOOP, 10, (task(1, "m.py:main:3", child),), running=2))

    text = str(q.tasks())
    assert "awaiting" in text
    assert "[pid 1, thread t1]" in text
    assert "  task-2 #2" in text

    data = json.loads(json.dumps(q.tasks().to_dict()))
    assert data["roots"][0]["children"][0]["task_id"] == 2


def test_task_stacks():
    worker = task(2, "w.py:worker:5;w.py:burst:6", name="worker")
    waiting = task(2, "w.py:worker:7;s.py:sleep:1", name="worker")
    q = wall(
        task_sample(LOOP, 10, (task(1, "m.py:main:3", worker, name="main"),), 2),
        task_sample(LOOP, 20, (task(1, "m.py:main:3", waiting, name="main"),)),
        task_sample(LOOP, 5, (task(1, "m.py:main:3", waiting, name="main"),), 1),
    )

    result = q.task_stacks("worker")
    assert result.matched == ("worker #2",)
    sleeping, running = result
    assert [str(_) for _ in sleeping.frames] == ["w.py:worker", "s.py:sleep"]
    assert (sleeping.value, sleeping.running, sleeping.awaiting) == (25, 0, 25)
    assert sleeping.samples == 2
    assert [str(_) for _ in running.frames] == ["w.py:worker", "w.py:burst"]
    assert (running.value, running.running, running.awaiting) == (10, 10, 0)

    every = q.task_stacks()
    assert every.matched == ("main #1", "worker #2")
    assert every.count == 3
    assert len(q.task_stacks(n=1)) == 1

    text = str(result)
    assert "running 0µs, awaiting 25µs" in text
    assert "note:" not in text
    assert "note: concurrent tasks" in str(every)


def test_task_stacks_cpu_has_no_await_time():
    worker = task(2, "w.py:worker:5", name="worker")
    q = ProfileQuery(
        [
            AustinMetadata("mode", "cpu"),
            task_sample(LOOP, 10, (task(1, "m.py:main:3", worker),), 2),
            task_sample(LOOP, 20, (task(1, "m.py:main:3", worker),)),
        ]
    )

    (stack,) = q.task_stacks("worker")
    assert (stack.value, stack.running, stack.awaiting) == (10, 10, 0)
    assert "awaiting" not in str(q.task_stacks())


def test_unknown_task_selector():
    q = wall(task_sample(LOOP, 10, (task(1, "m.py:main:3", name="worker-0"),)))

    with pytest.raises(NoMatchError, match="did you mean one of: worker-0"):
        q.filter(task="worker0")
    with pytest.raises(NoMatchError, match="No tasks match"):
        q.task_stacks("nothing")
    with pytest.raises(NoMatchError, match="has no asyncio tasks"):
        wall(sample("a.py:f:1", 10)).task_stacks("worker")
