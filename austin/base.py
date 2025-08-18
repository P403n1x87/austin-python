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


import functools
import os
import sys
from abc import ABC
from abc import abstractmethod
from enum import Enum
from itertools import takewhile
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from austin.cli import AustinArguments
from austin.config import AustinConfiguration
from austin.errors import AustinError
from austin.events import AustinMetadata
from austin.events import AustinSample


SemVer = Tuple[int, int, int]


def _to_semver(version: Optional[str]) -> SemVer:
    if version is None:
        return (0, 0, 0)

    try:
        return (
            tuple(
                int(_)
                for _ in "".join(
                    list(
                        takewhile(
                            lambda _: _.isdigit() or _ == ".", version.replace("?", "0")
                        )
                    )
                ).split(".")
            )
            + (0, 0, 0)
        )[
            # type: ignore[return-value]
            :3
        ]
    except ValueError:
        raise ValueError("Invalid semantic version") from None


class AustinState(int, Enum):
    """Austin state."""

    NOT_STARTED = 0
    STARTING = 1
    RUNNING = 2
    TERMINATING = 3
    TERMINATED = 4


_EXE_EXT = ".exe" if sys.platform == "win32" else ""


class BaseAustin(ABC):
    """Base Austin class.

    Defines the general API that abstract Austin as an external process.
    Subclasses should implement the :func:`start` and :func:`terminate` methods,
    and either define the :func:`on_sample` method or pass it via the
    constructor. Additionally, the :func:`on_metadata` :func:`on_terminate`
    methods can be overridden or passed via the constructor to catch metadata
    and termination events respectively. Austin is considered to be ready when
    the first metadata event is received, and the `start` function returns, and
    it is considered to have terminated when the Austin process has terminated
    gracefully.

    If an error was encountered, the :class:`AustinError` exception is thrown.
    """

    BINARY = Path("austin").with_suffix(_EXE_EXT)
    MINIMUM_BINARY_VERSION: SemVer = (4, 0, 0)

    def __init__(
        self,
        sample_callback: Optional[Callable[[AustinSample], None]] = None,
        metadata_callback: Optional[Callable[[AustinMetadata], None]] = None,
        terminate_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """The ``BaseAustin`` constructor.

        The callbacks can be passed as arguments, if they are not
        defined/overridden in the definition of a sub-class.
        """
        self._args: Optional[AustinArguments] = None
        self._meta: Dict[str, str] = {}

        if sample_callback is None and not hasattr(self, "on_sample"):
            msg = "No mandatory sample callback given or implemented."
            raise AustinError(msg)

        self._sample_callback = sample_callback or self.on_sample  # type: ignore[attr-defined]

        self._metadata_callback = metadata_callback or getattr(
            self, "on_metadata", None
        )
        self._terminate_callback = terminate_callback or getattr(
            self, "on_terminate", None
        )

        self._state: AustinState = AustinState.NOT_STARTED

    @abstractmethod
    def start(self, args: Optional[List[str]] = None) -> Any:
        """Start Austin.

        Every subclass should implement this method and ensure that it spawns
        a new Austin process.
        """
        ...

    def get_arguments(self) -> Optional[AustinArguments]:
        """Get the inferred command line.

        Return the command line of the (main) process that is being profiled
        by Austin.
        """
        return self._args

    def is_running(self) -> bool:
        """Determine whether Austin is running."""
        return self._state is AustinState.RUNNING

    @abstractmethod
    def terminate(self) -> Any:
        """Terminate Austin.

        Stop the underlying Austin process by sending a termination signal.
        """
        ...

    @abstractmethod
    def wait(self) -> Any:
        """Wait for Austin to terminate.

        This method blocks until the Austin process has terminated.
        Returns the exit code of the Austin process.
        """
        ...

    def _check_version(self) -> None:
        """Check for the minimum Austin binary version."""
        austin_version = self.version
        if austin_version is None:
            raise AustinError("Cannot determine Austin version")
        if austin_version < self.MINIMUM_BINARY_VERSION:
            raise AustinError(
                f"Incompatible Austin version (got {austin_version}, expected >= {self.MINIMUM_BINARY_VERSION})"
            )

    # ---- Properties ----

    @functools.cached_property
    def binary_path(self) -> Path:
        """Discover the path of the Austin binary.

        Lookup order is:
        - current working directory
        - ``AUSTINPATH`` variable
        - ``~/.austinrc`` file
        - ``PATH`` variable.
        """
        binary_name = self.BINARY

        # Try CWD
        binary_path = binary_name.resolve()
        if binary_path.is_file():
            return binary_path

        # Try with AUSTINPATH variable
        austin_path = os.environ.get("AUSTINPATH", None)
        if austin_path:
            binary_path = Path(austin_path).expanduser().resolve() / binary_name
            if binary_path.is_file():
                return binary_path

        # Try with .austinrc file
        if AustinConfiguration().binary is not None:
            binary_path = Path(AustinConfiguration().binary).expanduser().resolve()
            if binary_path.is_file():
                return binary_path

        # Try from PATH
        return self.BINARY

    @functools.cached_property
    def version(self) -> SemVer:
        """Austin version."""
        try:
            return _to_semver(self._meta.get("austin"))
        except KeyError as exc:
            raise AustinError("Austin version not set") from exc

    @functools.cached_property
    def python_version(self) -> SemVer:
        """The version of the detected Python interpreter."""
        try:
            return _to_semver(self._meta.get("python"))
        except KeyError as exc:
            raise AustinError("Python version not set") from exc

    @property
    def state(self) -> AustinState:
        """The current state of Austin."""
        return self._state
