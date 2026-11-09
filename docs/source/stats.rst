.. _stats:

Collecting Statistics
=====================

This package provides classes for basic operations with the samples collected by
Austin.


Overview
--------

The wrapper classes pass the samples collected by Austin to the sample callback
as :class:`austin.events.AustinSample` objects (see :ref:`events`). You can use
:class:`austin.stats.AustinStats` objects to aggregate the profiling metrics
they carry, like own and total time, by passing them to the
:func:`austin.stats.AustinStats.update` method. Each
:class:`austin.stats.AustinStats` object aggregates a single kind of metric,
given by its :class:`austin.stats.AustinStatsType`: wall-clock time, CPU time,
allocated memory or deallocated memory. The following is a simple example of an
``on_sample`` callback implemented on an Austin wrapper object that passes the
incoming samples to an :class:`austin.stats.AustinStats` object for
aggregation::

  from austin.events import AustinSample
  from austin.simple import SimpleAustin
  from austin.stats import AustinStats
  from austin.stats import AustinStatsType


  class MySimpleAustin(SimpleAustin):
      def __init__(self, *args, **kwargs):
          super().__init__(*args, **kwargs)

          self._stats = AustinStats(AustinStatsType.WALL)

      def on_sample(self, sample: AustinSample) -> None:
          self._stats.update(sample)

      def on_terminate(self) -> None:
          def print_frames(framestats, depth=0):
              frame = framestats.label
              print(
                  f"  {framestats.own:>12}  {framestats.total:>12}  "
                  f"{'  ' * depth}{frame.function} ({frame.filename}:{frame.line})"
              )
              for child in framestats.children.values():
                  print_frames(child, depth + 1)

          for pid, process in self._stats.processes.items():
              print(f"Process {pid}")
              for thread_info, thread in process.threads.items():
                  print(f"Thread {thread_info.thread}")
                  print(f"  {'OWN (us)':>12}  {'TOTAL (us)':>12}  FRAME")
                  for framestats in thread.children.values():
                      print_frames(framestats)


  austin = MySimpleAustin()
  austin.start(["python3", "-c", "for _ in range(100000): print(_)"])
  austin.wait()


You can then collect the aggregated figures from the
:class:`austin.stats.AustinStats` object by navigating the processes and threads
that have been profiled. You start by selecting or looping over the observed
processes via the ``processes`` dictionary. This maps PIDs to
:class:`austin.stats.ProcessStats` objects holding the process statistics.
Each :class:`austin.stats.ProcessStats` object has a dictionary ``threads`` of
all the observed threads within that process. This maps ``ThreadInfo`` named
tuples, made of the thread name and the sub-interpreter ID, to
:class:`austin.stats.ThreadStats` objects. The ``label`` attribute is the
``ThreadInfo`` of the thread, while the frame stack can be navigated using the
``children`` attribute. This maps :class:`austin.events.AustinFrame` objects to
:class:`austin.stats.FrameStats` objects holding the aggregated statistics of
each observed frame within the thread. The ``own`` and ``total`` attributes are
in microseconds for time statistics and in bytes for memory statistics.

The example above shows you how to use the ``on_terminate`` callback to navigate
the collected statistics and print a simple report once Austin has terminated.

If you have the output of a previous run of Austin, you can also use
:func:`austin.stats.AustinStats.load` to aggregate all of its samples in one go.


The ``austin.stats`` sub-module
-------------------------------

.. automodule:: austin.stats
    :members:
    :show-inheritance:
