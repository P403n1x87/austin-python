# This file is part of "austin-python" which is released under GPL.
#
# See file LICENCE or go to http://www.gnu.org/licenses/ for full license
# details.
#
# austin-python is a Python wrapper around Austin, the CPython frame stack
# sampler.
#
# Copyright (c) 2018-2020 Gabriele N. Tornetta <phoenix1987@gmail.com>.
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from os import path

from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="austin-python",
    version="0.1.0",
    description=("Python wrapper for Austin, the frame stack sampler for CPython"),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/P403n1x87/austin-python",
    author="Gabriele N. Tornetta",
    author_email="phoenix1987@gmail.com",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GPLv3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    keywords="profiler stack sampler",
    packages=find_packages(exclude=["docs", "test"]),
    include_package_data=True,
    python_requires=">=3.6",
    install_requires=["dataclasses", "psutil"],
    extras_require={"test": ["pytest-cov", "tox-travis", "coveralls"]},
    entry_points={"console_scripts": ["austin2ss=austin.format.speedscope:main"]},
    project_urls={
        "Bug Reports": "https://github.com/P403n1x87/austin-python/issues",
        "Source": "https://github.com/P403n1x87/austin-python",
    },
)
