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

from austin.format.compress import compress
from austin.stats import AustinFileReader


def test_compress(datapath):
    with AustinFileReader(datapath / "austin.out") as original:
        compressed = io.StringIO()
        compress(original, compressed)

        with open(datapath / "austin.out") as original:
            compressed_value = compressed.getvalue()
            assert compressed_value
            assert len(compressed_value.splitlines()) < len(original.readlines())


def test_compress_counts(datapath):
    with AustinFileReader(datapath / "austin.out") as original:
        compressed = io.StringIO()
        compress(original, compressed, counts=True)

        for sample in compressed.getvalue().splitlines():
            head, _, metric = sample.rpartition(" ")
            if (
                head == "P4317;T7ffb7f8f0700;"
                "_bootstrap (/usr/lib/python3.6/threading.py);L884;"
                "_bootstrap_inner (/usr/lib/python3.6/threading.py);L916;"
                "run (/usr/lib/python3.6/threading.py);L864;"
                "keep_cpu_busy (../austin/test/target34.py);L31"
            ):
                assert int(metric) == 20
                break
