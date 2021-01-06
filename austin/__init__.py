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


from abc import ABC, abstractmethod
import argparse
import functools
import os
import os.path
from typing import Any, Callable, List, Optional, Tuple

from austin.config import AustinConfiguration
import psutil


try:
    _cached = functools.cache
except AttributeError:
    _cached = functools.lru_cache(maxsize=1)


class AustinError(Exception):
    """Basic Austin Error."""

    pass


class AustinTerminated(AustinError):
    """Austin termination exception.

    Thrown when Austin is terminated with a call to ``terminate``.
    """

    pass


class BaseAustin(ABC):
    """Base Austin class.

    Defines the general API that abstract Austin as an external process.
    Subclasses should implement the :func:`start` method and either define the
    :func:`on_sample_received` method or pass it via the constructor.
    Additionally, the :func:`on_ready` and the :func:`on_terminate` methods can
    be overridden or passed via the constructor to catch the corresponding
    events. Austin is considered to be ready when the first sample is received;
    it is considered to have terminated when the process has terminated
    gracefully.

    If an error was encountered, the :class:`AustinError` exception is thrown.
    """

    BINARY = "austin"

    def __init__(
        self,
        sample_callback: Callable[[str], None] = None,
        ready_callback: Callable[[psutil.Process, psutil.Process, str], None] = None,
        terminate_callback: Callable[[str], None] = None,
    ) -> None:
        """The ``BaseAustin`` constructor.

        The callbacks can be passed as arguments, if they are not
        defined/overridden in the definition of a sub-class.
        """
        self._proc: psutil.Process = None
        self._child_proc: psutil.Process = None
        self._cmd_line: Optional[str] = None
        self._running: bool = False

        try:
            self._sample_callback = sample_callback or self.on_sample_received
        except AttributeError:
            raise AustinError("No sample callback given or implemented.")

        self._terminate_callback = terminate_callback or self.on_terminate
        self._ready_callback = ready_callback or self.on_ready

        self._version: Optional[str] = None
        self._python_version: Optional[str] = None

    def _get_process_info(
        self, args: argparse.Namespace, austin_pid: int
    ) -> Tuple[psutil.Process, psutil.Process, str]:
        try:
            self._proc = psutil.Process(austin_pid)
        except psutil.NoSuchProcess:
            raise AustinError("Cannot find Austin process.")

        if not args.pid:  # Austin is forking
            try:
                self._child_proc = self._proc.children()[0]
                if self._child_proc is None:
                    raise IndexError
            except IndexError:
                raise AustinError("Cannot find Austin child process.")
        else:  # Austin is attaching
            try:
                self._child_proc = psutil.Process(args.pid)
            except psutil.NoSuchProcess:
                raise AustinError(
                    f"Cannot attach to process with invalid PID {args.pid}."
                )

        self._cmd_line = " ".join(self._child_proc.cmdline())

        self._running = True

        return self._proc, self._child_proc, self._cmd_line

    @abstractmethod
    def start(self, args: List[str] = None) -> Any:
        """Start Austin.

        Every subclass should implement this method and ensure that it spawns
        a new Austin process.
        """
        ...

    def get_process(self) -> psutil.Process:
        """Get the underlying Austin process.

        Return an instance of :class:`psuitl.Process` that can be used to
        control the underlying Austin process at the OS level.
        """
        return self._proc

    def get_command_line(self) -> Optional[str]:
        """Get the inferred command line.

        Return the command line of the (main) process that is being profiled
        by Austin.
        """
        return self._cmd_line

    def is_running(self) -> bool:
        """Determine whether Austin is running."""
        return self._running

    def terminate(self, wait: bool = False) -> None:
        """Terminate Austin.

        Stop the underlying Austin process by sending a termination signal.
        """
        if not self._proc:
            raise AustinError("Austin has not been started yet")

        try:
            self._proc.terminate()
            if wait:
                self._proc.wait()
        except psutil.NoSuchProcess:
            raise AustinError("Austin has already terminated")

        self._running = False
        self._proc = None
        self._child_proc = None

    def get_child_process(self) -> psutil.Process:
        """Get the child process.

        Return an instalce of :class:`psutil.Process` representing the (main)
        process being profiled by Austin at the OS level.
        """
        return self._child_proc

    def submit_sample(self, data: bytes) -> None:
        """Submit a sample to the sample callback.

        This method takes care of converting the raw binary data retrieved from
        Austin into a Python string.
        """
        try:
            sample = data.decode()
        except UnicodeDecodeError:
            try:
                sample = data.decode("ascii")
            except UnicodeDecodeError:
                return

        self._sample_callback(sample.rstrip())

    # ---- Default callbacks ----

    def on_terminate(self, stats: str) -> Any:
        """Terminate event callback.

        Implement to be notified when Austin has terminated gracefully. The
        callback accepts an argument that will receive the global statistics.
        """
        pass

    def on_ready(
        self,
        process: psutil.Process,
        child_process: psutil.Process,
        command_line: str,
        data: Any = None,
    ) -> Any:
        """Ready event callback.

        Implement to get notified when Austin has successfully started or
        attached the Python process to profile and the first sample has been
        produced. This callback receives the Austin process and it's (main)
        profiled process as instances of :class:`psutil.Process`, along with
        the command line of the latter.
        """
        pass

    # ---- Properties ----

    @property
    @_cached
    def binary_path(self) -> str:
        """Discover the path of the Austin binary.

        Lookup order is:
        - current working directory
        - ``AUSTINPATH`` variable
        - ``~/.austinrc`` file
        - ``PATH`` variable.
        """
        binary_name = self.BINARY + (os.name == "nt" and ".exe" or "")

        # Try CWD
        binary_path = os.path.join(os.getcwd(), binary_name)
        if os.path.isfile(binary_path):
            return binary_path

        # Try with AUSTINPATH variable
        austin_path = os.environ.get("AUSTINPATH", None)
        if austin_path:
            binary_path = os.path.join(os.path.expanduser(austin_path), binary_name)
            if os.path.isfile(binary_path):
                return binary_path

        # Try with .austinrc file
        if AustinConfiguration().binary is not None:
            binary_path = os.path.expanduser(AustinConfiguration().binary)
            if os.path.isfile(binary_path):
                return binary_path

        # Try from PATH
        return self.BINARY

    @property
    def version(self) -> Optional[str]:
        """Austin version."""
        return self._version

    @property
    def python_version(self) -> Optional[str]:
        """The version of the detected Python interpreter."""
        return self._python_version
