.. _cli:

Command Line Argument Parsing
=============================


If you are developing a command-line utility around Austin and you would like to
use `argparse <https://docs.python.org/3/library/argparse.html>`_ to parse
the command-line arguments, you can customise the
:class:`austin.cli.AustinArgumentParser` class to easily parse and validate
arguments that need to be passed to the Austin binary. You can remove the Austin
arguments that you don't need by setting the corresponding argument of the
constructor to ``False``. Similarly, if you need to add extra arguments or
options, you can use the ``add_argument`` method of the base
``argparse.ArgumentParser`` class.


The ``austin.cli.AustinArgumentParser`` class
---------------------------------------------

.. autoclass:: austin.cli.AustinArgumentParser
    :members:
    :show-inheritance:
