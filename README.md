<p align="center">
  <br>
  <img src="docs/source/images/logo.png" alt="Austin">
  <br>
</p>

<h3 align="center">Python wrapper for Austin, the frame stack sampler for CPython</h3>

<p align="center">
  <a href="https://github.com/P403n1x87/austin-python/actions?workflow=Tests">
    <img src="https://github.com/P403n1x87/austin-python/workflows/Tests/badge.svg"
         alt="GitHub Actions: Tests">
  </a>
  <a href="https://codecov.io/gh/P403n1x87/austin-python">
    <img src="https://codecov.io/gh/P403n1x87/austin-python/branch/master/graph/badge.svg"
         alt="Codecov">
  </a>
  <a href="https://pypi.org/project/austin-python/">
    <img src="https://img.shields.io/pypi/v/austin-python.svg"
         alt="PyPI">
  </a>
  <a href="https://austin-python.readthedocs.io/">
    <img src="https://readthedocs.org/projects/austin-python/badge/"
         alt="LICENSE">
  </a>
  <a href="https://github.com/P403n1x87/austin-python/blob/master/LICENSE.md">
    <img src="https://img.shields.io/badge/license-GPLv3-ff69b4.svg"
         alt="LICENSE">
  </a>
</p>

<p align="center">
  <a href="https://snapcraft.io/austin" title="Get it from the Snap Store">
    <img src="https://snapcraft.io/static/images/badges/en/snap-store-black.svg" alt="" />
  </a>
</p>

<p align="center">
  <a href="#synopsis"><b>Synopsis</b></a>&nbsp;&bull;
  <a href="#installation"><b>Installation</b></a>&nbsp;&bull;
  <a href="#usage"><b>Usage</b></a>&nbsp;&bull;
  <a href="#compatibility"><b>Compatibility</b></a>&nbsp;&bull;
  <a href="#why--austin"><b>Why <img src="art/austin_logo.svg" height="20px" /> Austin</b></a>&nbsp;&bull;
  <a href="#examples"><b>Examples</b></a>&nbsp;&bull;
  <a href="#contribute"><b>Contribute</b></a>
</p>

<p align="center">
  <a href="https://www.patreon.com/bePatron?u=19221563">
    <img src="https://img.shields.io/endpoint.svg?url=https%3A%2F%2Fshieldsio-patreon.herokuapp.com%2FP403n1x87&style=for-the-badge" />
  </a><br/>

  <a href="https://www.buymeacoffee.com/Q9C1Hnm28" target="_blank">
    <img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" />
  </a>
</p>


<!--

![austin](art/austin.png)

<h3 align="center">A frame stack sampler for CPython</h3>

[![Build Status](https://travis-ci.org/P403n1x87/austin.svg?branch=master)](https://travis-ci.org/P403n1x87/austin) ![Version](https://img.shields.io/badge/version-1.0.0-blue.svg) [![License](https://img.shields.io/badge/license-GPLv3-ff69b4.svg)](https://github.com/P403n1x87/austin/blob/master/LICENSE.md)

-->


# Synopsis



# Installation


# Usage


# Compatibility




# Examples



## Speedscope

Austin output format can be converted easily into the
[Speedscope](speedscope.app) JSON format. You can find a sample utility along
with the TUI and Austin Web.

If you want to give it a go you can install it using `pip` with

~~~ bash
pip install git+https://github.com/P403n1x87/austin.git --upgrade
~~~

and run it with

~~~ bash
austin2speedscope [-h] [--indent INDENT] [-V] input output
~~~

where `input` is a file containing the output from Austin and `output` is the
name of the JSON file to use to save the result of the conversion, ready to be
used on [Speedscope](speedscope.app).

<p align="center"><img src="art/speedscope.png" /></p>

# Contribute

If you like Austin and you find it useful, there are ways for you to contribute.

If you want to help with the development, then have a look at the open issues
and have a look at the [contributing guidelines](CONTRIBUTING.md) before you
open a pull request.

You can also contribute to the development of Austin by either [becoming a
Patron](https://www.patreon.com/bePatron?u=19221563) on Patreon

<a href="https://www.patreon.com/bePatron?u=19221563">
  <img src="https://img.shields.io/endpoint.svg?url=https%3A%2F%2Fshieldsio-patreon.herokuapp.com%2FP403n1x87&style=for-the-badge" />
</a><br/>

by [buying me a coffee](https://www.buymeacoffee.com/Q9C1Hnm28) on BMC

<a href="https://www.buymeacoffee.com/Q9C1Hnm28" target="_blank">
  <img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" />
</a>

or by chipping in a few pennies on
[PayPal.Me](https://www.paypal.me/gtornetta/1).
