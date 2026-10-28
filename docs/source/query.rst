.. _query:

Querying Profiles
=================

The :class:`austin.query.ProfileQuery` class answers the most common questions
about a profile without having to aggregate samples by hand. It takes the events
produced by any Austin event iterator, so it works with MOJO files, collapsed
stack files and live Austin runs alike::

  from austin.query import ProfileQuery

  q = ProfileQuery.from_file("profile.mojo")

  print(q.summary())                # mode, metrics, totals per thread
  print(q.top(10))                  # hottest functions by own value
  print(q.top(10, by="total"))      # ... or by total value
  print(q.stacks(5))                # heaviest distinct stacks
  print(q.callers("db.py:execute")) # who calls a function
  print(q.callees("db.py:execute")) # what a function calls
  print(q.lines("db.py:execute"))   # hottest lines in a function
  print(q.tree(min_pct=5))          # call tree, pruned below 5%
  print(q.tasks())                  # asyncio task trees (Python 3.14+)
  print(q.task_stacks("worker-0"))  # where a task ran and awaited

Every query returns a result object that renders as a compact text table when
printed, and that can be converted to JSON-ready data with ``to_dict()``. The
entries of a result are also available as typed objects by iterating over it.


Metrics
-------

Queries take an optional ``metric`` argument, either an
:class:`austin.stats.AustinStatsType` or one of the strings ``wall``, ``cpu``,
``memory`` (or ``alloc``) and ``dealloc``. When omitted, it defaults to the
metric of the profile mode, which is wall time for full-mode profiles and
allocated memory for memory-mode profiles.


Selectors
---------

Frames are referred to by selectors. A selector is either

- a string of the form ``function``, ``file:function`` or
  ``file:function:line``, where ``file`` matches any path suffix and
  ``function`` also matches qualified names ending in ``.function``;
- a string ``re:<pattern>``, matched against ``file:function:line``;
- a :class:`austin.query.Location` or an :class:`austin.events.AustinFrame`;
- a predicate over :class:`austin.events.AustinFrame` objects.

When a selector matches more than one function, the query aggregates over all
of them and lists what it matched. Use :meth:`austin.query.ProfileQuery.find`
to check what a selector matches. A selector that matches nothing raises
:class:`austin.query.NoMatchError`, with suggestions for similar function names.


Filtering
---------

:meth:`austin.query.ProfileQuery.filter` returns a new query over the samples
that match all the given criteria, e.g. a process, a thread, the idle or GC
state, or the presence of a frame. Percentages are always relative to the total
of the queried profile::

  main = q.filter(thread="main", idle=False)
  print(main.top(10))
  print(q.filter(contains="requests").callers("send"))


Paths
-----

Rendered results show shortened file paths. Each path is made relative to the
longest root that contains it: the entries of the ``pythonpath``, the ``cwd``
and the ``venv`` recorded in the profile metadata, when available, and the
``site-packages`` and standard library folders of Python source files. Paths
are extended as needed so that each one still selects a single file, so they can
be used as selectors. The data returned by ``to_dict()`` always uses full paths.
Pass ``short_paths=False`` to :class:`austin.query.ProfileQuery` to render full
paths too.


asyncio Tasks
-------------

On Python 3.14 and later, Austin also samples asyncio tasks. Austin reports the
frames of a running task as the task's position rather than as part of its
thread stack, which then ends in the event loop. The queries put them back
together: in a sample in which a task was running, the stack is the thread
stack followed by the frames of the running task. This way, ``top``,
``stacks``, ``callers`` and the other queries show the code that was actually
running.

:meth:`austin.query.ProfileQuery.tasks` returns the task trees of the profile,
where each task is a child of the task that awaits it, and the root tasks are
grouped by the thread that owns them::

  print(q.tasks())

Each task has a *running* value, i.e. the value of the samples in which it was
running, and, in wall time, an *awaiting* value, i.e. the time it was alive
without running. In wall time, the total of a task is the time it was alive,
which already includes the time it spent awaiting its children. For every
other metric, the total of a task is its own running value plus the totals of
the tasks it awaited.

:meth:`austin.query.ProfileQuery.task_stacks` shows where tasks spent their
time. A task's position is its coroutine chain while it is suspended, or the
frames it is running. Each position gets the running time of the tasks that
were running there and, in wall time, the time tasks were suspended there,
e.g. awaiting a sleep, a lock or a socket. This answers questions like "which
``await`` is this task stuck on"::

  print(q.task_stacks("worker-0"))      # where a task ran and awaited
  print(q.task_stacks("re:^worker-", 5)) # merged across matching tasks

Concurrent tasks are alive at the same time, so in wall time the values of the
positions of several tasks can add up to more than the profile total.

The ``task`` filter keeps the samples in which a given task was *running*, so
that any other query can be narrowed down to the code it ran. A task that only
ever awaited has no such samples: use ``task_stacks`` for it instead::

  print(q.filter(task="worker-0").top(10))
  print(q.filter(task="re:^worker-").stacks(5))

Tasks are selected by ID, by name, by a regular expression on the name
(``re:<pattern>``), or by a predicate over :class:`austin.events.AustinTask`
objects. A task selector that matches no task raises
:class:`austin.query.NoMatchError`, with suggestions for similar task names.


Command Line
------------

The ``austin-query`` command runs the same queries on a profile file, one
sub-command per query. Filters and output options can come after the
sub-command, and ``--json`` prints compact JSON instead of text, e.g.::

  austin-query profile.mojo summary
  austin-query profile.mojo top -n 20 --by total
  austin-query profile.mojo callers db.py:execute --thread main
  austin-query profile.mojo tasks
  austin-query profile.mojo task-stacks worker-0 --json
  austin-query profile.mojo top --gc

``austin-query --help`` explains the selector syntax and suggests a workflow,
which makes the command a convenient way for coding agents to look into a
profile. Errors, like selectors that match nothing, go to the standard error
with a non-zero exit status.


Recursion
---------

Totals are recursion-safe: a function that appears more than once in a stack
counts that stack only once, and so does every caller and callee edge.


The ``austin.query`` sub-module
-------------------------------

.. automodule:: austin.query
    :members: ProfileQuery, Location, NoMatchError, ROOT, SELF, matcher,
        task_matcher, TopResult, TopEntry, StacksResult, Stack, Neighbours,
        Edge, CallTree, CallNode, TasksResult, TaskNode, TaskStacksResult,
        TaskStack, Summary, MetricSummary, ThreadSummary
