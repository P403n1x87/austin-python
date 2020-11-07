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


import os.path

import toml


class AustinConfigurationError(Exception):
    """Austin configuration error."""

    pass


class AustinConfiguration:
    """Austin configuration borg."""

    RC = os.path.join(os.path.expanduser("~"), ".austinrc")

    __borg__ = {}

    def __init__(self) -> None:
        self.__dict__ = self.__borg__
        self.reload()

    def reload(self) -> None:
        """Reload the configuration from the run-control file."""
        try:
            with open(self.RC) as fin:
                self._data = toml.load(fin)
        except FileNotFoundError:
            self._data = {}

    def save(self) -> None:
        """Save the current configuration to file."""
        try:
            with open(self.RC, "w") as fout:
                toml.dump(self._data, fout)
        except Exception as e:
            raise AustinConfigurationError("Unable to save Austin configuration") from e

    @property
    def binary(self) -> str:
        """Get the Austin binary path."""
        return self._data.get("binary", None)
