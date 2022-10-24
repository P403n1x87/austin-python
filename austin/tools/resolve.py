# This file is part of "austin-python" which is released under GPL.
#
# See file LICENCE or go to http://www.gnu.org/licenses/ for full license
# details.
#
# austin-python is a Python wrapper around Austin, the CPython frame stack
# sampler.
#
# Copyright (c) 2018-2022 Gabriele N. Tornetta <phoenix1987@gmail.com>.
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

import typing as t
from subprocess import check_output

from austin.format.mojo import MojoFile
from austin.format.mojo import MojoFrame
from austin.format.mojo import MojoMetadata
from austin.format.mojo import MojoString
from austin.format.mojo import to_varint


__version__ = "0.1.0"


def demangle_cython(function: str) -> str:
    """Demangle a Cython functio nanme."""
    if function.startswith("__pyx_pymod_"):
        _, _, function = function[12:].partition("_")
        return function

    if function.startswith("__pyx_fuse_"):
        function = function[function[12:].index("__pyx_") + 12 :]
    for _i, d in enumerate(function):
        if d.isdigit():
            break
    else:
        raise ValueError(f"Invalid Cython mangled name: {function}")

    n = 0
    while _i < len(function):
        c = function[_i]
        _i += 1
        if c.isdigit():
            n = n * 10 + int(c)
        else:
            _i += n
            n = 0
            if not function[_i].isdigit():
                return function[_i:]

    return function


class Maps:
    """Keep mappings between objects to resolve."""

    def __init__(self) -> None:
        # TODO: Use an interval tree instead!
        self.maps: t.List[t.Tuple[int, int, str]] = []
        self.bases: t.Dict[str, int] = {}
        self.cache: t.Dict[str, t.Optional[t.Tuple[str, t.Optional[int]]]] = {}
        self.lines: t.Dict[int, bytes] = {}

    def addr2line(self, address: str) -> t.Optional[t.Tuple[str, t.Optional[int]]]:
        if address in self.cache:
            return self.cache[address]

        addr = int(address, 16)
        for lo, hi, _binary in self.maps:
            if lo <= addr <= hi:
                break
        else:
            self.cache[address] = None
            return None

        resolved, _, _ = (
            check_output(["addr2line", "-Ce", _binary, f"{addr-self.bases[_binary]:x}"])
            .decode()
            .strip()
            .partition(" ")
        )
        if resolved.startswith("??"):
            # self.cache[address] = (f"{binary}@{addr-self.bases[binary]:x}", None)
            self.cache[address] = (f"{_binary}", addr - self.bases[_binary])
            return self.cache[address]

        symbol, line = tuple(resolved.split(":", maxsplit=1))
        self.cache[address] = (symbol, int(line) if line is not None else 0)
        return self.cache[address]

    def add(self, line: str) -> None:
        bounds, _, binary = line[7:].strip().partition(" ")
        low, _, high = bounds.partition("-")
        lo = int(low, 16)
        hi = int(high, 16)
        self.maps.append((lo, hi, binary))
        if binary in self.bases:
            self.bases[binary] = min(self.bases[binary], lo)
        else:
            self.bases[binary] = lo

    def resolve(self, line: str) -> str:
        parts = []
        frames, _, metrics = line.strip().rpartition(" ")
        for part in frames.split(";"):
            try:
                head, function, lineno = part.split(":")
            except ValueError:
                parts.append(part)
                continue
            if function.startswith("__pyx_pw_") or function.startswith("__pyx_pf_"):
                # skip Cython wrappers (cpdef)
                continue
            if function.startswith("__pyx_"):
                function = demangle_cython(function)
            if head.startswith("native@"):
                _, _, address = head.partition("@")
                resolved = self.addr2line(address)
                if resolved is None:
                    parts.append(":".join((head, function, lineno)))
                else:
                    source, native_lineno = resolved
                    parts.append(f"{source}:{function}:{native_lineno or lineno}")
            else:
                parts.append(":".join((head, function, lineno)))

        return " ".join((";".join(parts), metrics))

    def resolve_string(self, string: MojoString) -> t.Optional[tuple]:
        value = string.value
        if value.startswith("__pyx_") and not (
            value.startswith("__pyx_pw_") or value.startswith("__pyx_pf_")
        ):
            return (None, demangle_cython(value), None)

        if value.startswith("native@"):
            _, _, address = value.partition("@")
            resolved = self.addr2line(address)
            if resolved is not None:
                filename, line = resolved
                return (filename, None, int(line) if line is not None else 0)

        return None


def resolve_mojo(input: str, output: str) -> None:
    maps = Maps()
    with open(input, "rb") as mojo, open(output, "wb") as fout:
        mojo_file = MojoFile(mojo)  # Fails if not a MOJO file

        # Write the MOJO header
        fout.write(mojo_file.header)

        # Echo events and intercepts strings that need to be resolved
        for event in mojo_file.parse():
            if isinstance(event, MojoMetadata) and event.key == "map":
                maps.add(event.to_austin())

            elif isinstance(event, MojoString):
                resolved = maps.resolve_string(event)
                if resolved is not None:
                    filename, scope, line = resolved
                    new_value = filename or scope

                    event.raw = event.raw.replace(
                        event.value.encode(), new_value.encode()
                    )

                    if filename is not None:
                        maps.lines[event.key] = to_varint(line)

            elif isinstance(event, MojoFrame):
                if event.filename.string.key in maps.lines:
                    event.raw = (
                        event.raw[: -len(to_varint(event.line))]
                        + maps.lines[event.filename.string.key]
                    )

            fout.write(event.raw)


def resolve_austin(input: str, output: str) -> None:
    maps = Maps()
    with open(input) as fin, open(output, "w") as fout:
        for line in fin:
            if line.startswith("# map: "):
                maps.add(line)
            elif line.startswith("# ") or line == "\n":
                print(line, end="", file=fout)
            else:
                print(maps.resolve(line), file=fout)


def main() -> None:
    from argparse import ArgumentParser

    arg_parser = ArgumentParser(
        prog="austinp-resolve",
        description="Resolve native symbols in austinp sample files.",
    )

    arg_parser.add_argument(
        "input",
        type=str,
        help="The input file to resolve.",
    )
    arg_parser.add_argument(
        "output", type=str, help="The path of the resolved file to write to."
    )

    arg_parser.add_argument("-V", "--version", action="version", version=__version__)

    args = arg_parser.parse_args()

    try:
        try:
            resolve_mojo(args.input, args.output)
        except Exception:
            resolve_austin(args.input, args.output)
    except FileNotFoundError:
        print(f"No such input file: {args.input}")
        exit(1)
    except Exception as e:
        print(f"File format not recognised: {e}")
        exit(1)


if __name__ == "__main__":
    main()
