.. _events:

Austin Events
=============

The wrapper classes decode the output of the Austin binary into a stream of
events, which are then passed to the callbacks described in
:ref:`wrapper_classes`. There are two kinds of events:

- :class:`austin.events.AustinMetadata` events carry the metadata emitted by
  Austin, such as the sampling mode or the sampling interval, as ``name`` and
  ``value`` pairs;
- :class:`austin.events.AustinSample` events carry the samples collected by
  Austin.

Each sample records the process ID (``pid``), the sub-interpreter ID (``iid``)
and the name of the thread (``thread``) that has been sampled, together with
the collected ``metrics`` and the frame stack, ``frames``. The metrics are
represented by :class:`austin.events.AustinMetrics` objects, with ``time``
measured in microseconds and ``memory`` in bytes, while the frame stack is a
tuple of :class:`austin.events.AustinFrame` objects, ordered from the outermost
frame to the innermost one. The ``gc`` and ``idle`` flags tell whether the
garbage collector was running and whether the thread was idle when the sample
was taken.

When profiling ``asyncio`` applications on Python 3.14 and later, samples also
carry information about the asyncio tasks owned by the sampled thread. See
:class:`austin.events.AustinTask` and :class:`austin.events.AustinTaskReport`
for more details.


The ``austin.events`` sub-module
--------------------------------

.. automodule:: austin.events
    :members: AustinEvent, AustinMetadata, AustinSample, AustinMetrics,
        AustinFrame, AustinTask, AustinTaskReport
    :member-order: bysource
    :show-inheritance:
