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

import io
from pathlib import Path

from austin.format.collapsed_stack import AustinFileReader
from austin.format.compress import compress


def test_compress(datapath: Path):
    with AustinFileReader((datapath / "austin.out").open()) as original:
        compressed = io.StringIO()
        compress(original, compressed)

        compressed_value = compressed.getvalue()
        assert compressed_value
        assert len(compressed_value.splitlines()) < len(
            (datapath / "austin.out").open().readlines()
        )


def test_compress_counts(datapath: Path):
    with AustinFileReader((datapath / "austin.out").open()) as original:
        compressed = io.StringIO()
        compress(original, compressed, counts=True)

        for sample in compressed.getvalue().splitlines():
            head, _, metric = sample.rpartition(" ")
            if (
                head == "P82848;T534600;"
                "/home/gabriele/Projects/austin/test/target34.py:<module>:38;"
                "/home/gabriele/Projects/austin/test/target34.py:keep_cpu_busy:32"
            ):
                assert int(metric) == 19
                break
        else:
            print(compressed.getvalue())
            msg = "Expected sample not found in compressed output"
            raise AssertionError(msg)
