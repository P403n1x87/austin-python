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

from austin.format.pprof import PProf
from austin.stats import AustinFileReader
from austin.stats import InvalidSample
from austin.stats import MetricType
from austin.stats import Sample


def test_pprof(datapath):
    with AustinFileReader(datapath / "austin.out") as austin:
        mode = austin.metadata["mode"]
        prof = PProf(mode)

        for line in austin:
            try:
                prof.add_samples(Sample.parse(line, MetricType.from_mode(mode)))
            except InvalidSample:
                continue

        bstream = io.BytesIO()
        prof.dump(bstream)

        with open(datapath / "austin.pprof", "rb") as pprof:
            assert pprof.read() == bstream.getvalue()
