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
from unittest.mock import patch

import pytest

from austin.format.collapsed_stack import AustinFileReader
from austin.format.compress import compress
from austin.format.compress import main


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


def test_compress_main(datapath: Path, tmp_path: Path):
    output = tmp_path / "output.out"
    with patch(
        "sys.argv", ["austin-compress", str(datapath / "austin.out"), str(output)]
    ):
        main()
    assert output.exists()
    assert output.stat().st_size > 0


def test_compress_main_counts(datapath: Path, tmp_path: Path):
    output = tmp_path / "output_counts.out"
    with patch(
        "sys.argv",
        ["austin-compress", "--counts", str(datapath / "austin.out"), str(output)],
    ):
        main()
    assert output.exists()


def test_compress_main_missing_file(tmp_path: Path):
    missing = tmp_path / "nonexistent.out"
    output = tmp_path / "out.out"
    with patch("sys.argv", ["austin-compress", str(missing), str(output)]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
