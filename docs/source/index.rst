.. image:: images/logo.png
   :align: center

.. raw:: html

  <h3 align="center">Python wrapper for Austin, the frame stack sampler for CPython</h3>

  <p align="center">
    <a href="https://travis-ci.com/P403n1x87/austin-python">
      <img src="https://travis-ci.com/P403n1x87/austin-python.svg?token=fzW2yzQyjwys4tWf9anS&branch=master"
           alt="Travis CI Build Status"/>
    </a>
    <img src="https://img.shields.io/badge/coverage-99%25-green.svg"
         alt="Test coverage at 99%">
    <a href="https://badge.fury.io/py/austin-python">
      <img src="https://badge.fury.io/py/austin-python.svg" alt="PyPI version">
    </a>
    <a href="http://pepy.tech/project/austin-python">
      <img src="http://pepy.tech/badge/austin-python"
           alt="PyPI Downloads">
    </a>
    <img src="https://img.shields.io/badge/version-0.1.0-blue.svg"
         alt="Version 0.1.0">
    <a href="https://github.com/P403n1x87/austin-python/blob/master/LICENSE.md">
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

Finally, when you install this package, you also get the ``austin2speedscope``
utility installed. This allows you to convert samples collected with Austin to
the `Speedscope <https://www.speedscope.app/>`_. Note that
`Speedscope <https://www.speedscope.app/>`_ can also handle the output generated
by Austin directly
(see `Importing from custom sources <https://github.com/jlfwong/speedscope/wiki/Importing-from-custom-sources>`_
for details).

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
