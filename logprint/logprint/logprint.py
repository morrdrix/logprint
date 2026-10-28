"""Mirror print-style output to a UTF-8 log file.

Copyright (c) 2020 Julian Klein. Distributed under the MIT license.
"""

from __future__ import annotations

import builtins
import datetime
import io
import os
import sys
import threading
import warnings
from types import TracebackType
from typing import Any, TextIO

__version__ = "2.0.0"


class LogPrint:
    """Mirror messages to enabled destinations with explicit file ownership.

    File errors propagate to the caller. Use a context manager or close()
    explicitly. External output streams are never owned by this class.
    """

    def __init__(
        self,
        file: str | os.PathLike[str] | None = "log.txt",
        write_mode: str = "a",
        print_header: bool = False,
    ) -> None:
        if not isinstance(print_header, bool):
            raise TypeError("print_header must be a bool")
        if write_mode not in ("a", "w", "x"):
            raise ValueError("write_mode must be 'a', 'w', or 'x'")

        self._lock = threading.RLock()
        self._closed = False
        self.script_name = sys.argv[0] if sys.argv else ""
        self.file_name = file
        self.file_hnd: TextIO | None = None
        self._configuration: dict[str, Any] = {
            "timestamp_format": "[%Y-%m-%d %H:%M:%S]",
            "timestamp": False,
            "screen": True,
            "log_to_file": file is not None,
        }
        if file is not None:
            self.file_hnd = open(file, write_mode, encoding="utf-8")
        if print_header:
            try:
                self.print(f"logging {self.script_name} to {self.file_name}")
            except BaseException:
                self.close()
                raise

    @property
    def closed(self) -> bool:
        """Whether this logger has been explicitly closed."""
        return self._closed

    @property
    def configuration(self) -> dict[str, Any]:
        """Return a snapshot; use set_config() to change configuration."""
        with self._lock:
            return self._configuration.copy()

    def _normalize_options(self, options: dict[str, Any]) -> dict[str, Any]:
        options = options.copy()
        if "file" in options:
            if "log_to_file" in options:
                raise TypeError("Use only log_to_file, not both file and log_to_file")
            warnings.warn(
                "The boolean 'file' option is deprecated; use log_to_file instead",
                DeprecationWarning,
                stacklevel=3,
            )
            options["log_to_file"] = options.pop("file")
        for key, value in options.items():
            if key not in self._configuration:
                raise TypeError(f"Unknown configuration option: {key}")
            if key == "timestamp_format":
                if not isinstance(value, str):
                    raise TypeError("timestamp_format must be a str")
            elif not isinstance(value, bool):
                raise TypeError(f"{key} must be a bool")
        if options.get("log_to_file") and self.file_hnd is None:
            raise ValueError("Cannot enable file logging: no log file was opened")
        return options

    def set_config(self, **kwargs: Any) -> None:
        """Validate and atomically update persistent output options."""
        with self._lock:
            self._ensure_open()
            self._configuration.update(self._normalize_options(kwargs))

    def set_temp_config(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        """Return temporary options and standard print arguments without saving."""
        with self._lock:
            self._ensure_open()
            print_kwargs = {
                key: value
                for key, value in kwargs.items()
                if key in {"sep", "end", "flush"} or (key == "file" and not isinstance(value, bool))
            }
            options = {key: value for key, value in kwargs.items() if key not in print_kwargs}
            config = self._configuration.copy()
            config.update(self._normalize_options(options))
            return config, print_kwargs

    def _ensure_open(self) -> None:
        if self.closed:
            raise ValueError("I/O operation on closed LogPrint")

    def print(
        self,
        *args: Any,
        sep: str | None = " ",
        end: str | None = "\n",
        file: TextIO | None = None,
        flush: bool = False,
        **kwargs: Any,
    ) -> None:
        """Print to file (or current stdout) and mirror to the enabled log file.

        sep, end, and flush follow built-in print semantics. Output options can
        be overridden for this call. file=bool is a deprecated legacy option.
        """
        with self._lock:
            self._ensure_open()
            if isinstance(file, bool):
                kwargs["file"] = file
                file = None
            config = self._configuration.copy()
            config.update(self._normalize_options(kwargs))
            destination = sys.stdout if file is None else file
            if destination is not None and not callable(getattr(destination, "write", None)):
                raise AttributeError("Output stream must have a write() method")

            # Render once so stateful __str__ methods cannot diverge per output.
            buffer = io.StringIO()
            if config["timestamp"]:
                args = (datetime.datetime.now().strftime(config["timestamp_format"]), *args)
            builtins.print(*args, sep=sep, end=end, file=buffer)
            message = buffer.getvalue()
            streams = []
            if config["screen"] and destination is not None:
                streams.append(destination)
            if config["log_to_file"] and self.file_hnd is not None:
                if all(stream is not self.file_hnd for stream in streams):
                    streams.append(self.file_hnd)
            for stream in streams:
                stream.write(message)
                if flush:
                    stream.flush()

    def flush(self) -> None:
        """Flush the owned log file; external streams remain caller-managed."""
        with self._lock:
            self._ensure_open()
            if self.file_hnd is not None:
                self.file_hnd.flush()

    def close(self) -> None:
        """Close the owned file. Repeated calls are harmless."""
        with self._lock:
            if not self.closed:
                if self.file_hnd is not None:
                    self.file_hnd.close()
                self._closed = True

    def __enter__(self) -> LogPrint:
        self._ensure_open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
