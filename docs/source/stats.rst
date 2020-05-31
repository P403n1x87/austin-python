.. _stats:

Collecting Statistics
=====================

This package provides classes for basic operations with the samples collected by
Austin.


Overview
--------

Raw samples collected by Austin can be parsed into its many components with the
:func:`austin.stats.Sample.parse` static method, which returns a
:class:`austin.stats.Sample` object. This is a data class with fields such as
``pid``, ``thread``, ``metrics`` and ``frames``, representing the different
parts of an Austin sample.

You can use :class:`austin.stats.AustinStats` objects to aggregate profiling
metrics, like own and total time, by providing it with
:class:`austin.stats.Sample` objects via the
:func:`austin.stats.AustinStats.update` method. The following is a simple
example of a ``on_sample_received`` callback implemented on an Austin wrapper
object that parses the incoming samples and pass them to an
:class:`austin.stats.AustinStats` for aggregation::

  from datetime import timedelta as td

  from austin.simple import SimpleAustin
  from austin.stats import AustinStats, InvalidSample, Sample


  class MySimpleAustin(SimpleAustin):
      def __init__(self, *args, **kwargs):
          super().__init__(*args, **kwargs)

          self._stats = AustinStats()
          self._sample_count = 0
          self._error_count = 0

      def on_sample_received(self, text):
          try:
              self._stats.update(Sample.parse(text))
              self._sample_count += 1
          except InvalidSample:
              self._error_count += 1

      def on_terminate(self, *args, **kwargs):

          def print_frames(framestats):
              print("    {own: >16}  {total: >16}  {frame}".format(
                  own=str(td(seconds=framestats.own.time/1e6)),
                  total=str(td(seconds=framestats.total.time/1e6)),
                  frame=framestats.label
              ))
              for _, child in framestats.children.items():
                  print_frames(child)

          for pid, process in self._stats.processes.items():
              print(f"Process {pid or self.proc.pid}")
              for tid, thread in process.threads.items():
                  print(f"  {tid}")
                  print(f"    {'OWN':^16}  {'TOTAL':^16}  {'FRAME'}")
                  for _, framestats in thread.children.items():
                      print_frames(framestats)


  MySimpleAustin().start(["python3", "-c", "for _ in range(10000): print(_)"])


You can then collect the aggregated figures from the
:class:`austin.stats.AustinStats` object by navigating the processes and threads
that have been profiled. You start by selecting or looping over the observed
processes via the ``processes`` dictionary. This maps PIDs to
:class:`austin.stats.ProcessStats` objects holding the process statistics.
Each :class:`austin.stats.ProcessStats` object has a dictionary `threads` of
all the observed threads within that process. This maps thread names to
:class:`austin.stats.ThreadStats` objects. The ``label`` attribute is just the
thread name, while the frame stack can be navigated using the ``children``
attribute. This maps :class:`austin.stats.Frame` objects to
:class:`austin.stats.FrameStats` objects holding the aggregated statistics of
each observed frame within the thread.

The example above shows you how to use the
:func:`austin.BaseAustin.on_terminate` callback to navigate the collected
statistics and print a simple report once Austin has terminated.


The ``austin.stats`` sub-module
-------------------------------

.. automodule:: austin.stats
    :members:
    :show-inheritance:
