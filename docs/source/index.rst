.. image:: images/logo.png
   :align: center

.. raw:: html

  <h3 align="center">Python wrapper for Austin, the frame stack sampler for CPython</h3>

  <p align="center">
    <a href="https://github.com/P403n1x87/austin-python/actions?workflow=Tests">
      <img src="https://github.com/P403n1x87/austin-python/workflows/Tests/badge.svg"
           alt="GitHub Actions: Tests">
    </a>
    <a href="https://travis-ci.org/P403n1x87/austin-python">
      <img src="https://travis-ci.org/P403n1x87/austin-python.svg?branch=main"
           alt="Travis CI">
    </a>
    <a href="https://codecov.io/gh/P403n1x87/austin-python">
      <img src="https://codecov.io/gh/P403n1x87/austin-python/branch/main/graph/badge.svg"
           alt="Codecov">
    </a>
    <a href="https://austin-python.readthedocs.io/">
      <img src="https://readthedocs.org/projects/austin-python/badge/"
           alt="Documentation">
    </a>
    <br/>
    <a href="https://pypi.org/project/austin-python/">
      <img src="https://img.shields.io/pypi/v/austin-python.svg"
           alt="PyPI">
    </a>
    <a href="https://pepy.tech/project/austin-python">
      <img src="https://static.pepy.tech/personalized-badge/austin-python?period=total&units=international_system&left_color=grey&right_color=blue&left_text=downloads"
           alt="Downloads" />
    <a/>
    <br/>
    <a href="https://github.com/P403n1x87/austin-python/blob/main/LICENSE.md">
      <img src="https://img.shields.io/badge/license-GPLv3-ff69b4.svg"
           alt="LICENSE">
    </a>
  </p>


This Python package is a wrapper around
`Austin <https://github.com/P403n1x87/austin>`_, the CPython frame stack
sampler. You can use the classes provided by this package to quickly integrate
or extend Austin's statistical profiling capabilities with Python to suit all
your needs.

In most cases you should be able to use one of the wrapper classes that are
provided with this package out of the box. All you have to do is focus on your
business logic while the classes take care of the boilerplate code to start
Austin in the background and collect samples from it. You can choose from either
a thread-based or an asyncio-based interface, depending on your preference. The
section on :ref:`wrapper_classes` provides more details as well as some basic
examples on how to use each of them.

To assist you with the development of command-line tools that leverage the
profiling capabilities of Austin, the package also provides the ``austin.cli``
sub-module. There you can find the :class:`austin.cli.AustinArgumentParser``,
which is a sub-class of ``argparse.ArgumentParser``. If you want to customise
it to meet your needs, simply sub-class it and tweak it as discused in
:ref:`cli`.

Finally, when you install this package, you also get the ``austin-compress``,
``austin2speedscope`` and ``austin2pprof`` command line tools. The first allows
you to compress the  raw samples collected by Austin by performing aggregation
of the metrics; the others allow you to convert Austin samples to the
`Speedscope <https://www.speedscope.app/>`_ and the Google `pprof
<https://github.com/google/pprof>`_ formats respectively. Note that `Speedscope
<https://www.speedscope.app/>`_ can also handle the output generated by Austin
directly (see `Importing from custom sources
<https://github.com/jlfwong/speedscope/wiki/Importing-from-custom-sources>`_ for
details).

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   wrapper_classes
   stats
   cli



Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
