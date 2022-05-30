.. _wrapper_classes:

Wrapper Classes
===============

This section describe the three wrapper classes that are provided by this
Python package. In most cases, you should be able to just grab one of them and
implement a few callbacks or overrides some methods in your subclasses to
interact with the Austin binary.

If you want to make your own implementation of the wrapper, the
:class:`austin.BaseAustin` abstract base class can provide you with a good
starting point.

.. note::
    For the wrappers to work as expected, the Austin binary needs to be
    locatable from the following sources, in the given order

    - current working directory;
    - the ``AUSTINPATH`` environment variable which gives the path to the folder
      that contains the Austin binary;
    - the ``.austinrc`` TOML configuration file in the user's home folder, e.g.
      ``~/.austinrc`` on Linux (:ref:`see below <austinrc>`);
    - the ``PATH`` environment variable.


The Abstract Austin Base Class
------------------------------

.. autoclass:: austin.BaseAustin
    :members:
    :undoc-members:

All the wrappers documented in this section are subclasses of the
:class:`austin.BaseAustin` class. The purpose is to set a common base API while
also providing some convenience methods that you are likely to need, so that
you don't have to implement them yourself.

The ``start`` method
~~~~~~~~~~~~~~~~~~~~

The general idea is to subclass :class:`austin.BaseAustin` and subclass the
:func:`austin.BaseAustin.start` method with the logic required to start the
Austin binary in the background. By default, Austin's binary is named
``austin``, and you can refer to it with ``BaseAustin.BINARY``. Hence, if you
were to start Austin in an asyncio fashion, your start method would be a
coroutine starting with::

    async def start(self, args: List[str] = []) -> None:
        try:
            self.proc = await asyncio.create_subprocess_exec(
                self.BINARY,
                *(args or sys.argv[1:]),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            raise AustinError("Austin executable not found.")

You should use the optional ``args`` argument to pass in the command-line
arguments to pass to the Austin binary, as done in the above example.

.. note::
    For the wrappers to work as expected, the Austin binary specified by the
    ``BINARY`` class attribute needs to be on the ``PATH`` environment variable
    or they will fail to start. Of course, this value can be overridden by
    sub-classes so that this behaviour can be adjusted according to your needs.

The callbacks
~~~~~~~~~~~~~

The other requirement for making a subclass of :class:`austin.BaseAustin`
concrete is the implementation of the ``on_sample_received`` callback. This
can either be a class method, or passed via the ``sample_callback`` argument
to the constructor of the subclass. This callback function must take a single
argument of type ``str``, which holds the raw text of a sample collected by
Austin.

There are other two recommended callbacks that you might want to implement:
:func:`austin.BaseAustin.on_ready` and :func:`austin.BaseAustin.on_terminate`.
See the class documentation below for more details.


The Simple Austin Wrapper
-------------------------

.. autoclass:: austin.simple.SimpleAustin
    :members:
    :show-inheritance:

The :class:`austin.simple.SimpleAustin` wrapper is for simple applications that
do not require any sort of concurrency or (thread-based) parallelism. For
example, your application does not involve a user interface or asynchronous I/O.

The example above shows you how to make a simple echo Austin application that
effectively acts like the underlying Austin binary. The ``on_sample_received``
is indeed echoing back all the samples that it receives


The ``asyncio``-based Austin Wrapper
------------------------------------

.. autoclass:: austin.aio.AsyncAustin
    :members:
    :show-inheritance:

This wrapper implements an ``asyncio``-based API around Austin. The ``start``
method is, in fact, a coroutine that can be schedule with any ``asyncio``
event loops.

The example above shows how to implement the same echo example of the simple
case using this wrapper.


The Thread-based Austin Wrapper
-------------------------------

.. autoclass:: austin.threads.ThreadedAustin
    :members:
    :show-inheritance:

This wrapper implements an thread-based API around Austin. This class offers
additional methods beside the base API of :class:`austin.BaseAustin` that allow
you to perform operations that are typical of thread-based applications, like
joining a thread to ensure a proper termination of the application.

The example above shows how to implement the same echo example of the simple
case using this wrapper.


.. _austinrc:

``.austinrc``
-------------

The ``.austinrc`` run-control file located in the user's home folder can be used
to configure the wrappers. The basic implementation of
:class:`austin.config.AustinConfiguration` supports the option `binary` to
specify the location of the Austin binary. This is the third lookup option when
trying to locate the Austin binary in order to start sampling, as discussed at
the top of this page.

.. autoclass:: austin.config.AustinConfiguration
    :members:
    :show-inheritance:

Applications that need custom configuration can sub-class
:class:`austin.config.AustinConfiguration` and modify the internal state
`self._data`, which is then dumped to back to the `.austinrc` file via a call to
`save`. The file format is TOML.
