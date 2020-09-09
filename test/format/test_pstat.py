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

from austin.format.pstat import Pstats
from austin.stats import Sample


def test_pstat_full_metrics():
    pstats = Pstats()
    for sample in ["P42;T123;foo (foo_module.py:10) 10 20 -30"]:
        pstats.add_sample(Sample.parse(sample))
    assert pstats.asdict() == {('foo_module.py', 10, 'foo'): (1, 1, 0, 0, {})}


def test_pstat_full_metrics_alloc_dealloc():
    pstats = Pstats()
    for sample in [
        "P42;T123;foo (foo_module.py:10) 10 20 0",
        "P42;T321;foo (foo_module.py:10) 10 0 -30",
    ]:
        pstats.add_sample(Sample.parse(sample))
    assert pstats.asdict() == {}
