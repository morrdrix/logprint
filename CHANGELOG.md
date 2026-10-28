# Changelog

## 2.0.0

### Changed

- Append to existing log files by default; select write_mode="w" explicitly to truncate.
- Use log_to_file for the logging toggle. file=stream now selects the screen
  destination, while the message is still mirrored unless log_to_file=False.
- Honor flush=False by default. Call flush(), pass flush=True, or close the
  logger to make buffered file output available.
- Return a configuration snapshot; use set_config() for validated updates.
- Raise errors for failed file opening, invalid options, and use after closing.
- Remove the global instance restriction.

### Added and fixed

- Context manager, idempotent close(), explicit flush(), and screen-only file=None mode.
- Fix the string-valued print_header default; it is now the boolean False.
- Render each message once for identical screen/file text.
- Serialize calls and configuration changes on each instance.
- Deprecation warnings for legacy boolean file options; migrate to log_to_file.
- Installable package, public LogPrint import, regression tests, and CI.

No release has been published as part of this local change.
