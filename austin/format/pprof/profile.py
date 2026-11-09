# This file is part of "austin-python" which is released under GPL.
#
# See file LICENCE or go to http://www.gnu.org/licenses/ for full license
# details.
#
# austin-python is a Python wrapper around Austin, the CPython frame stack
# sampler.
#
# Copyright (c) 2018-2026 Gabriele N. Tornetta <phoenix1987@gmail.com>.
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

"""Minimal pprof protobuf messages.

This is a dependency-free implementation of the subset of the messages in
``profile.proto`` that is needed to produce pprof profiles. Messages are
serialised with the same field ordering and encoding rules used by the
reference protobuf implementation, so the output is byte-for-byte identical.
"""

import typing as t
from dataclasses import dataclass
from dataclasses import field

# Wire types
VARINT = 0
LEN = 2

# Field kinds
SCALAR = 0  # singular varint, omitted when zero
STRING = 1  # repeated string, always emitted
MESSAGE = 2  # repeated message, always emitted
PACKED = 3  # repeated varint, packed, omitted when empty


def _varint(n: int) -> bytes:
    # Negative int64 values are encoded as their 64-bit two's complement.
    n &= 0xFFFFFFFFFFFFFFFF
    buffer = bytearray()
    while n > 0x7F:
        buffer.append((n & 0x7F) | 0x80)
        n >>= 7
    buffer.append(n)
    return bytes(buffer)


def _key(number: int, wire_type: int) -> bytes:
    return _varint((number << 3) | wire_type)


def _len_delimited(number: int, data: bytes) -> bytes:
    return _key(number, LEN) + _varint(len(data)) + data


class Message:
    """Base protobuf message."""

    # Field number, attribute name and kind, sorted by field number.
    __fields__: t.ClassVar[t.Tuple[t.Tuple[int, str, int], ...]] = ()

    def SerializeToString(self) -> bytes:  # noqa: N802
        """Serialise the message to the protobuf wire format."""
        buffer = bytearray()
        for number, name, kind in self.__fields__:
            value = getattr(self, name)
            if kind == SCALAR:
                if value:
                    buffer += _key(number, VARINT) + _varint(int(value))
            elif kind == STRING:
                for s in value:
                    buffer += _len_delimited(number, s.encode())
            elif kind == MESSAGE:
                for m in value:
                    buffer += _len_delimited(number, m.SerializeToString())
            elif kind == PACKED:
                if value:
                    buffer += _len_delimited(
                        number, b"".join(_varint(v) for v in value)
                    )
        return bytes(buffer)


@dataclass
class ValueType(Message):
    """Sample value type."""

    __fields__ = ((1, "type", SCALAR), (2, "unit", SCALAR))

    type: int = 0
    unit: int = 0


@dataclass
class Label(Message):
    """Sample label."""

    __fields__ = (
        (1, "key", SCALAR),
        (2, "str", SCALAR),
        (3, "num", SCALAR),
        (4, "num_unit", SCALAR),
    )

    key: int = 0
    str: int = 0
    num: int = 0
    num_unit: int = 0


@dataclass
class Sample(Message):
    """Profile sample."""

    __fields__ = (
        (1, "location_id", PACKED),
        (2, "value", PACKED),
        (3, "label", MESSAGE),
    )

    location_id: t.List[int] = field(default_factory=list)
    value: t.List[int] = field(default_factory=list)
    label: t.List[Label] = field(default_factory=list)


@dataclass
class Line(Message):
    """Location line."""

    __fields__ = ((1, "function_id", SCALAR), (2, "line", SCALAR))

    function_id: int = 0
    line: int = 0


@dataclass
class Location(Message):
    """Profile location."""

    __fields__ = (
        (1, "id", SCALAR),
        (2, "mapping_id", SCALAR),
        (3, "address", SCALAR),
        (4, "line", MESSAGE),
        (5, "is_folded", SCALAR),
    )

    id: int = 0
    mapping_id: int = 0
    address: int = 0
    line: t.List[Line] = field(default_factory=list)
    is_folded: bool = False


@dataclass
class Function(Message):
    """Profile function."""

    __fields__ = (
        (1, "id", SCALAR),
        (2, "name", SCALAR),
        (3, "system_name", SCALAR),
        (4, "filename", SCALAR),
        (5, "start_line", SCALAR),
    )

    id: int = 0
    name: int = 0
    system_name: int = 0
    filename: int = 0
    start_line: int = 0


@dataclass
class Profile(Message):
    """The pprof profile."""

    __fields__ = (
        (1, "sample_type", MESSAGE),
        (2, "sample", MESSAGE),
        (4, "location", MESSAGE),
        (5, "function", MESSAGE),
        (6, "string_table", STRING),
        (7, "drop_frames", SCALAR),
        (8, "keep_frames", SCALAR),
        (9, "time_nanos", SCALAR),
        (10, "duration_nanos", SCALAR),
        (12, "period", SCALAR),
        (13, "comment", PACKED),
        (14, "default_sample_type", SCALAR),
    )

    sample_type: t.List[ValueType] = field(default_factory=list)
    sample: t.List[Sample] = field(default_factory=list)
    location: t.List[Location] = field(default_factory=list)
    function: t.List[Function] = field(default_factory=list)
    string_table: t.List[str] = field(default_factory=list)
    drop_frames: int = 0
    keep_frames: int = 0
    time_nanos: int = 0
    duration_nanos: int = 0
    period: int = 0
    comment: t.List[int] = field(default_factory=list)
    default_sample_type: int = 0
