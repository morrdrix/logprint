# logprint

Mirror print-style output to a UTF-8 log file with a small, dependency-free Python
class. Requires Python 3.10 or newer.

## Installation

From the repository root:

```console
python -m pip install .
```

This checkout prepares version 2.0.0; it does not imply a release on PyPI.

## Quick start

```python
from logprint import LogPrint

with LogPrint("application.log") as log:
    print = log.print  # Local replacement; builtins.print is unchanged.
    print("Hello", 42)
    log.set_config(timestamp=True)
    print("Working", sep=" | ", flush=True)
    print("Screen only", log_to_file=False)
```

Existing log files are preserved: the default mode is append ("a").
Use write_mode="w" only when you deliberately want to replace the contents.
Mode "x" creates a new file and fails if it already exists.

## Constructor and ownership

```python
LogPrint(file="log.txt", write_mode="a", print_header=False)
```

- file accepts a path string or path-like object. Parent directories must exist.
- file=None explicitly enables screen-only operation without opening a log file.
- print_header=True writes a start message; the default is False.
- Opening errors such as FileNotFoundError and PermissionError propagate.
- Use with or close() to release the owned file. Repeated close() calls are safe.
- print(), flush(), and configuration changes after close() raise ValueError.
- Each instance owns its file; multiple independent instances are supported.

## Print arguments and output options

The standard sep, end, file, and flush arguments are supported. sep=None and
end=None use the built-in defaults. The default flush=False allows buffering.

```python
import sys
from logprint import LogPrint

with LogPrint("application.log") as log:
    log.print("An error", file=sys.stderr, flush=True)
    log.print("Only stderr", file=sys.stderr, log_to_file=False)
    log.print("Only the log", screen=False)
    log.flush()  # Flush the owned log file.
```

file=stream replaces the screen destination; logging still occurs unless
log_to_file=False. screen=False disables that screen destination too.
The external stream is never closed by LogPrint. log.flush() flushes only the
owned log file; print(..., flush=True) flushes every destination used by that call.

Configuration defaults:

| Option | Default | Meaning |
| --- | --- | --- |
| timestamp | False | Prefix each call with a local timestamp |
| timestamp_format | [%Y-%m-%d %H:%M:%S] | datetime.strftime format string |
| screen | True | Write to file=stream or current sys.stdout |
| log_to_file | True when a path is supplied | Mirror output to the owned file |

Use set_config(**options) for persistent settings, or pass these options to
print() for a single call. Unknown options and invalid value types raise
TypeError. Enabling file output on a file=None instance raises ValueError.

configuration returns a snapshot, so modifying it does not update the logger.
The retained set_temp_config(**options) method returns a configuration snapshot
and a separate dictionary of standard print arguments without saving changes.

## Compatibility and limits

This is a print-style mirroring utility, not a complete logging framework.
Messages are formatted once; every enabled destination receives the same text.
A timestamp is prepended once per call and uses the supplied sep.

Calls on one instance are serialized with a reentrant lock. Independent instances
or processes writing the same path are not coordinated; use separate paths or
a dedicated logging service for that case.

Writes to separate destinations are not atomic. A destination error propagates;
an earlier destination may already have received the message. No automatic retry
or silent fallback is performed. Text streams with a write() method are required;
stream encodings and newline translation remain the stream's responsibility.
Unlike built-in print, a message is formatted completely before any output is written.

## Migrating from 1.1.0

Version 2 introduces deliberate changes:

- The default mode changes from "w" to "a"; request "w" explicitly to truncate.
- print_header is a bool, not a string.
- Replace set_config(file=False) with set_config(log_to_file=False).
- Replace log.print(..., file=False) with log.print(..., log_to_file=False).
  Legacy boolean file options still work with DeprecationWarning and are
  scheduled for removal in the next major version.
- file=stream now selects the screen output stream.
- File output is no longer flushed automatically after each call. Use
  flush=True, log.flush(), or a context manager when immediate visibility matters.
- Multiple instances are allowed. Constructors no longer return None.
- Configuration updates must go through set_config(); invalid keys now fail early.
- Prefer from logprint import LogPrint. The installed
  from logprint.logprint import LogPrint import remains available.

## Development

```console
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m build --outdir output
```

CI is configured for Python 3.10-3.14 on Windows and Linux. This is a configured
matrix, not a claim that all combinations have already passed.
The runtime package has no third-party dependencies.

inputfiles/ is reserved for unchanged reference inputs. output/ holds generated
builds and reports; its contents are excluded from Git except the placeholder.

## License

MIT. Existing copyright notices are retained in LICENSE and logprint/LICENSE.txt.


