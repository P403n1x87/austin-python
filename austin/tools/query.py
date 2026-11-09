# This file is part of "austin-python" which is released under GPL.
#
# See file LICENCE or go to http://www.gnu.org/licenses/ for full license
# details.
#
# austin-python is a Python wrapper around Austin, the CPython frame stack
# sampler.
#
# Copyright (c) 2018-2026 Gabriele N. Tornetta <phoenix1987@gmail.com>.
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

"""Query Austin profiles from the command line.

Each sub-command runs the :class:`austin.query.ProfileQuery` query of the same
name on a MOJO or collapsed stack file, e.g.::

    austin-query profile.mojo top -n 10
    austin-query profile.mojo callers db.py:execute --thread main
    austin-query profile.mojo tasks --json
    austin-query profile.mojo task-stacks worker-0
"""

import json
import sys
import typing as t
from argparse import ArgumentParser
from argparse import Namespace
from argparse import RawDescriptionHelpFormatter

from austin.query import NoMatchError
from austin.query import ProfileQuery

EPILOG = """\
selectors (find, lines, callers, callees, tree, --contains):
  func, file:func, file:func:line
      file matches any path suffix, func also matches qualified names
      ending in .func (e.g. execute matches Cursor.execute)
  re:<pattern>
      regular expression matched against file:function:line

task selectors (task-stacks, --task):
  an ID, a name, or re:<pattern> matched against the name

typical workflow (options can also follow the sub-command):
  austin-query PROFILE summary          mode, metrics and threads
  austin-query PROFILE top -n 20        hottest functions (--by total for
                                        cumulative values)
  austin-query PROFILE callers FUNC     who calls a hot function; use
                                        callees and lines to drill down
  austin-query PROFILE stacks -n 5      heaviest full stacks

asyncio (Python 3.14+):
  austin-query PROFILE tasks            task trees, with running and
                                        awaiting time
  austin-query PROFILE task-stacks TASK where a task was running and
                                        awaiting
  austin-query PROFILE top --task TASK  hot code while a task was running

Add --json to any command for machine-readable output.
"""


def _int_or_str(value: str) -> t.Union[int, str]:
    return int(value) if value.isdigit() else value


def _parser() -> ArgumentParser:
    # Options shared by every sub-command, so that they can come after it.
    common = ArgumentParser(add_help=False)
    common.add_argument(
        "-m", "--metric", help="The metric to query (wall, cpu, memory, dealloc)"
    )
    common.add_argument("--json", action="store_true", help="Print the result as JSON")
    common.add_argument(
        "--full-paths", action="store_true", help="Do not shorten file paths"
    )
    filters = common.add_argument_group("filters")
    filters.add_argument("--pid", type=int, help="Keep the samples of a process")
    filters.add_argument("--thread", help="Keep the samples of a thread")
    filters.add_argument(
        "--task",
        type=_int_or_str,
        help="Keep the samples in which an asyncio task was running (see "
        "task-stacks for where it was awaiting too)",
    )
    filters.add_argument(
        "--contains", help="Keep the samples with a frame matching a selector"
    )
    filters.add_argument("--no-idle", action="store_true", help="Drop the idle samples")
    gc = filters.add_mutually_exclusive_group()
    gc.add_argument(
        "--gc",
        action="store_const",
        const=True,
        dest="gc",
        help="Keep the samples taken while the garbage collector was running",
    )
    gc.add_argument(
        "--no-gc",
        action="store_const",
        const=False,
        dest="gc",
        help="Drop the samples taken while the garbage collector was running",
    )

    argp = ArgumentParser(
        prog="austin-query",
        description="Query an Austin profile (MOJO or collapsed stacks)",
        epilog=EPILOG,
        formatter_class=RawDescriptionHelpFormatter,
    )
    argp.add_argument("profile", help="The profile file")
    commands = argp.add_subparsers(dest="command", required=True)

    def command(name: str, help: str) -> ArgumentParser:
        return commands.add_parser(
            name,
            parents=[common],
            help=help,
            description=help,
            epilog=EPILOG,
            formatter_class=RawDescriptionHelpFormatter,
        )

    command("summary", "Profile overview: mode, metrics and threads")

    top = command("top", "Hottest locations")
    top.add_argument("-n", type=int, default=20, help="Number of entries")
    top.add_argument("--by", choices=("own", "total"), default="own")
    top.add_argument("--lines", action="store_true", help="Lines, not functions")

    find = command("find", "Locations matching a selector")
    find.add_argument("selector")
    find.add_argument("--lines", action="store_true", help="Lines, not functions")

    lines = command("lines", "Line breakdown of the functions matching a selector")
    lines.add_argument("selector")

    stacks = command("stacks", "Heaviest stacks")
    stacks.add_argument("-n", type=int, default=10, help="Number of stacks")
    stacks.add_argument(
        "--per-thread", action="store_true", help="Keep threads separate"
    )
    stacks.add_argument("--lines", action="store_true", help="Lines, not functions")

    for kind in ("callers", "callees"):
        neighbours = command(kind, f"The {kind} of the functions matching a selector")
        neighbours.add_argument("selector")
        neighbours.add_argument(
            "--lines", action="store_true", help="Lines, not functions"
        )

    tree = command("tree", "Call tree, merged across threads")
    tree.add_argument("root", nargs="?", help="Root the tree at a selector")
    tree.add_argument("--max-depth", type=int, help="Maximum depth")
    tree.add_argument(
        "--min-pct", type=float, default=1.0, help="Prune nodes below this %%"
    )
    tree.add_argument("--lines", action="store_true", help="Lines, not functions")

    command("tasks", "asyncio task trees, with running and awaiting time")

    task_stacks = command(
        "task-stacks", "Where asyncio tasks were running and awaiting"
    )
    task_stacks.add_argument(
        "selector", nargs="?", type=_int_or_str, help="The tasks (default: all)"
    )
    task_stacks.add_argument("-n", type=int, default=10, help="Number of positions")
    task_stacks.add_argument(
        "--lines", action="store_true", help="Lines, not functions"
    )

    return argp


def _run(query: ProfileQuery, args: Namespace) -> t.Any:
    metric = args.metric
    command = args.command
    if command == "summary":
        return query.summary()
    if command == "top":
        return query.top(args.n, metric=metric, by=args.by, lines=args.lines)
    if command == "find":
        return query.find(args.selector, metric=metric, lines=args.lines)
    if command == "lines":
        return query.lines(args.selector, metric=metric)
    if command == "stacks":
        return query.stacks(
            args.n, metric=metric, per_thread=args.per_thread, lines=args.lines
        )
    if command == "callers":
        return query.callers(args.selector, metric=metric, lines=args.lines)
    if command == "callees":
        return query.callees(args.selector, metric=metric, lines=args.lines)
    if command == "tree":
        return query.tree(
            args.root,
            metric=metric,
            max_depth=args.max_depth,
            min_pct=args.min_pct,
            lines=args.lines,
        )
    if command == "tasks":
        return query.tasks(metric=metric)
    if command == "task-stacks":
        return query.task_stacks(args.selector, args.n, metric=metric, lines=args.lines)
    raise ValueError(f"Unknown command {command!r}")  # pragma: no cover


def main(argv: t.Optional[t.List[str]] = None) -> int:
    """Query an Austin profile."""
    args = _parser().parse_args(argv)

    try:
        query = ProfileQuery.from_file(args.profile, short_paths=not args.full_paths)
    except (OSError, ValueError) as e:
        print(f"austin-query: cannot read {args.profile}: {e}", file=sys.stderr)
        return 1

    try:
        filters = {
            "pid": args.pid,
            "thread": args.thread,
            "task": args.task,
            "contains": args.contains,
            "idle": False if args.no_idle else None,
            "gc": args.gc,
        }
        if any(_ is not None for _ in filters.values()):
            query = query.filter(**filters)
            if not query.samples:
                hint = (
                    "; the task never ran in them, see task-stacks for where it "
                    "was awaiting"
                    if args.task is not None
                    else ""
                )
                print(
                    f"austin-query: no samples match the filters{hint}", file=sys.stderr
                )
                return 1

        result = _run(query, args)
    except (NoMatchError, ValueError) as e:
        print(f"austin-query: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.to_dict(), separators=(",", ":")))
    else:
        print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
