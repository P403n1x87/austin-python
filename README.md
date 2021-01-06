<p align="center">
  <br/>
  <img src="docs/source/images/logo.png"
       alt="Austin"
       height="256px" />
  <br/>
</p>

<h3 align="center">Python wrapper for Austin</h3>

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

<p align="center">
  <a href="#synopsis"><b>Synopsis</b></a>&nbsp;&bull;
  <a href="#installation"><b>Installation</b></a>&nbsp;&bull;
  <a href="#usage"><b>Usage</b></a>&nbsp;&bull;
  <a href="#compatibility"><b>Compatibility</b></a>&nbsp;&bull;
  <a href="#documentation"><b>Documentation</b></a>&nbsp;&bull;
  <a href="#contribute"><b>Contribute</b></a>
</p>

<p align="center">
  <a href="https://www.buymeacoffee.com/Q9C1Hnm28" target="_blank">
    <img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" />
  </a>
</p>


# Synopsis

The `austin-python` package is a Python wrapper around the [Austin] binary that
provides convenience classes to quickly develop your statistical profiling
tools. Whether your code is thread-based or asynchronous, `austin-python` has
you covered. This is, for instance, how you would turn Austin into a Python
application:

~~~ python
from austin.aio import AsyncAustin


# Make your sub-class of AsyncAustin
class EchoAsyncAustin(AsyncAustin):
    def on_ready(self, process, child_process, command_line):
        print(f"Austin PID: {process.pid}")
        print(f"Python PID: {child_process.pid}")
        print(f"Command Line: {command_line}")

    def on_sample_received(self, line):
        print(line)

    def on_terminate(self, data):
        print(data)


# Use the Proactor event loop on Windows
if sys.platform == "win32":
    asyncio.set_event_loop(asyncio.ProactorEventLoop())

try:
    # Start the Austin application with some command line arguments
    austin = EchoAsyncAustin()
    asyncio.get_event_loop().run_until_complete(
        austin.start(["-i", "10000", "python3", "myscript.py"])
    )
except (KeyboardInterrupt, asyncio.CancelledError):
    pass
~~~

The `austin-python` package is at the heart of the [Austin
TUI](https://github.com/P403n1x87/austin-tui) and the [Austin
Web](https://github.com/P403n1x87/austin-web) Python applications. Go check them
out if you are looking for full-fledged usage examples.

Included with the package come two applications for the conversion of Austin
collected output, which is in the form of [collapsed
stacks](https://github.com/brendangregg/FlameGraph), to either the
[Speedscope](https://speedscope.app/) JSON format or the [Google pprof
format](https://github.com/google/pprof). Note, however, that the Speedscope web
application supports Austin native format directly.


# Installation

This package can be installed from PyPI with

~~~ bash
pip install --user austin-python --upgrade
~~~

Please note that `austin-python` requires the [Austin] binary. The default
lookup locations are, in order,

- current working directory;
- the `AUSTINPATH` environment variable which gives the path to the folder that
  contains the Austin binary;
- the `.austinrc` TOML configuration file in the user's home folder, e.g.
  `~/.austinrc` on Linux (see below for a sample `.austinrc` file);
- the `PATH` environment variable.

A sample `.austinrc` file would look like so

~~~ toml
binary = "/path/to/austin"
~~~


# Usage

A simple example of an echo application was shown above. Other examples using,
e.g., threads, can be found in the official documentation. You can also browse
through the code of the [Austin TUI](https://github.com/P403n1x87/austin-tui)
and the [Austin Web](https://github.com/P403n1x87/austin-web) Python
applications to see how they leverage `austin-python`.

## Format conversion

As it was mentioned before, this package also comes with two scripts for format
conversion, namely `austin2speedscope` and `austin2pprof`. They both take two
mandatory arguments, that is, the input and output file. For example, to convert
the Austin profile data file `myscript.aprof` to the Google pprof data file
`myscript.pprof`, you can run

~~~ bash
austin2pprof myscript.aprof myscript.pprof
~~~

The package also provide the `austin-compress` utility to compress the Austin
raw samples by aggregation.

# Compatibility

The `austin-python` package is tested on Linux, macOS and Windows with Python
3.6-3.9.


# Documentation

The official documentation is hosted on readthedocs.io at
[austin-python.readthedocs.io](https://austin-python.readthedocs.io/).


# Contribute

If you want to help with the development, then have a look at the open issues
and have a look at the [contributing guidelines](CONTRIBUTING.md) before you
open a pull request.

You can also contribute to the development by either [becoming a
Patron](https://www.patreon.com/bePatron?u=19221563) on Patreon, by [buying me a
coffee](https://www.buymeacoffee.com/Q9C1Hnm28) on BMC or by chipping in a few
pennies on [PayPal.Me](https://www.paypal.me/gtornetta/1).

<p align="center">
  <a href="https://www.buymeacoffee.com/Q9C1Hnm28" target="_blank">
    <img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png"
         alt="Buy Me A Coffee" />
  </a>
</p>


[Austin]: https://github.com/p403n1x87/austin
