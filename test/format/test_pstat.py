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


def test_pstat_simple():
    pstats = Pstats("test/data/simple.austin")
    pstats_dict = pstats.asdict()
    assert ('module1', 1, 'start') in pstats_dict
    prof = pstats.get_stats_profile()
    assert prof.func_profiles['run'].ncalls == 1

def test_pstat_full_metrics():
    pstats = Pstats("test/data/austin.out")
    pstats_dict = pstats.asdict()
    assert ('/usr/lib/python3.8/threading.py', 890, '_bootstrap') in pstats_dict
    top_level = pstats.stats.get_top_level_stats()
    prof = pstats.stats.get_stats_profile()
    assert prof.func_profiles['run'].ncalls == 1
