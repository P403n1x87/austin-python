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

import os
import os.path
import tempfile

import toml

from austin.config import AustinConfiguration as AC


def test_config_empty_binary():
    assert AC().binary is None


def test_config_binary(monkeypatch):
    home = tempfile.mkdtemp()
    monkeypatch.setenv("HOME", home)

    AC.RC = os.path.join(home, ".austinrc")
    with open(AC.RC, "w") as fout:
        toml.dump({"binary": "foo"}, fout)

    config = AC()
    config.reload()
    assert config.binary == "foo"
