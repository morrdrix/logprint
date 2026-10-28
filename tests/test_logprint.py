"""Regression tests for print semantics, file ownership, and configuration."""

import builtins
import contextlib
import io
from concurrent.futures import ThreadPoolExecutor

import pytest

from logprint import LogPrint, __version__


def test_public_import_and_version():
    assert __version__ == "2.0.0"


def test_default_has_no_header(tmp_path, capsys):
    path = tmp_path / "default.txt"
    with LogPrint(path):
        assert capsys.readouterr().out == ""
    assert path.read_text(encoding="utf-8") == ""


def test_header_is_opt_in(tmp_path, capsys):
    path = tmp_path / "header.txt"
    with LogPrint(path, print_header=True):
        output = capsys.readouterr().out
        assert output.startswith("logging ")
        assert str(path) in output
    assert path.read_text(encoding="utf-8") == output


def test_default_preserves_existing_log(tmp_path):
    path = tmp_path / "existing.txt"
    path.write_text("previous\n", encoding="utf-8")
    with LogPrint(path) as log:
        log.print("next", screen=False)
    assert path.read_text(encoding="utf-8") == "previous\nnext\n"


def test_explicit_overwrite(tmp_path):
    path = tmp_path / "existing.txt"
    path.write_text("previous", encoding="utf-8")
    with LogPrint(path, write_mode="w") as log:
        log.print("replacement", screen=False)
    assert path.read_text(encoding="utf-8") == "replacement\n"


def test_exclusive_mode_preserves_existing_file(tmp_path):
    path = tmp_path / "existing.txt"
    path.write_text("previous", encoding="utf-8")
    with pytest.raises(FileExistsError):
        LogPrint(path, write_mode="x")
    assert path.read_text(encoding="utf-8") == "previous"


def test_open_failure_propagates_without_console_fallback(tmp_path, capsys):
    with pytest.raises(FileNotFoundError):
        LogPrint(tmp_path / "missing" / "log.txt")
    assert capsys.readouterr() == ("", "")
    with LogPrint(tmp_path / "valid.txt"):
        pass


def test_permission_failure_propagates(monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError("permission denied")

    monkeypatch.setattr(builtins, "open", denied)
    with pytest.raises(PermissionError, match="permission denied"):
        LogPrint("unused.txt")


def test_independent_instances(tmp_path):
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    with LogPrint(first) as one, LogPrint(second) as two:
        one.print("one", screen=False)
        two.print("two", screen=False)
    assert first.read_text(encoding="utf-8") == "one\n"
    assert second.read_text(encoding="utf-8") == "two\n"


def test_external_stream_is_honored_and_not_closed(tmp_path, capsys):
    path = tmp_path / "mirror.txt"
    target = io.StringIO()
    with LogPrint(path) as log:
        log.print("redirected", file=target)
    assert target.getvalue() == "redirected\n"
    assert not target.closed
    assert capsys.readouterr().out == ""
    assert path.read_text(encoding="utf-8") == target.getvalue()


@pytest.mark.parametrize(
    ("args", "options"),
    [
        ((), {}),
        (("hello", 42, None), {}),
        (("one", "two"), {"sep": "|", "end": "<end>"}),
        (("one", "two"), {"sep": None, "end": None}),
        (("first\nsecond",), {"end": ""}),
        (("Grüße 日本語",), {}),
    ],
)
def test_standard_print_formatting(tmp_path, args, options):
    expected = io.StringIO()
    builtins.print(*args, file=expected, **options)
    path = tmp_path / "format.txt"
    actual = io.StringIO()
    with LogPrint(path) as log:
        log.print(*args, file=actual, **options)
    assert actual.getvalue() == expected.getvalue()
    assert path.read_text(encoding="utf-8") == expected.getvalue()


@pytest.mark.parametrize("options", [{"sep": 1}, {"end": 1}])
def test_invalid_print_arguments_write_nothing(tmp_path, options, capsys):
    path = tmp_path / "invalid.txt"
    with LogPrint(path) as log, pytest.raises(TypeError):
        log.print("message", **options)
    assert path.read_text(encoding="utf-8") == ""
    assert capsys.readouterr().out == ""


def test_message_is_rendered_once(tmp_path):
    class Changing:
        calls = 0

        def __str__(self):
            self.calls += 1
            return str(self.calls)

    path = tmp_path / "render.txt"
    target = io.StringIO()
    value = Changing()
    with LogPrint(path) as log:
        log.print(value, file=target)
    assert value.calls == 1
    assert target.getvalue() == path.read_text(encoding="utf-8") == "1\n"


def test_temporary_configuration_does_not_leak(tmp_path, capsys):
    path = tmp_path / "temporary.txt"
    with LogPrint(path) as log:
        log.set_config(timestamp=True, timestamp_format="STAMP")
        log.print("temporary", timestamp=False, screen=False)
        log.print("persistent")
    assert capsys.readouterr().out == "STAMP persistent\n"
    assert path.read_text(encoding="utf-8") == "temporary\nSTAMP persistent\n"


def test_log_to_file_can_be_temporarily_disabled(tmp_path, capsys):
    path = tmp_path / "disabled.txt"
    with LogPrint(path) as log:
        log.print("screen only", log_to_file=False)
        log.print("both")
    assert capsys.readouterr().out == "screen only\nboth\n"
    assert path.read_text(encoding="utf-8") == "both\n"


def test_legacy_boolean_file_options_warn(tmp_path, capsys):
    path = tmp_path / "legacy.txt"
    with LogPrint(path) as log:
        with pytest.warns(DeprecationWarning, match="log_to_file"):
            log.set_config(file=False)
        log.print("screen only")
        with pytest.warns(DeprecationWarning, match="log_to_file"):
            log.print("both", file=True)
        assert log.configuration["log_to_file"] is False
    assert capsys.readouterr().out == "screen only\nboth\n"
    assert path.read_text(encoding="utf-8") == "both\n"


def test_conflicting_legacy_and_new_options_rejected(tmp_path):
    with LogPrint(tmp_path / "conflict.txt") as log:
        with pytest.raises(TypeError, match="both"):
            log.print("message", file=False, log_to_file=True)


@pytest.mark.parametrize("method", ["set_config", "set_temp_config", "print"])
def test_unknown_option_is_rejected(tmp_path, method):
    with LogPrint(tmp_path / "unknown.txt") as log:
        with pytest.raises(TypeError, match="screeen"):
            getattr(log, method)(screeen=False)


@pytest.mark.parametrize(
    "options",
    [
        {"screen": "false"},
        {"timestamp": 1},
        {"timestamp_format": None},
        {"log_to_file": "yes"},
    ],
)
def test_invalid_config_types_are_rejected_atomically(tmp_path, options):
    with LogPrint(tmp_path / "types.txt") as log:
        before = log.configuration
        with pytest.raises(TypeError):
            log.set_config(**options)
        assert log.configuration == before


def test_configuration_snapshot_and_temporary_split(tmp_path):
    with LogPrint(tmp_path / "config.txt") as log:
        snapshot = log.configuration
        snapshot["screen"] = False
        stream = io.StringIO()
        config, kwargs = log.set_temp_config(screen=False, sep="|", file=stream)
        assert config["screen"] is False
        assert kwargs == {"sep": "|", "file": stream}
        assert log.configuration["screen"] is True


def test_flush_reaches_both_destinations_only_when_requested(tmp_path):
    class CountingStream(io.StringIO):
        flush_calls = 0

        def flush(self):
            self.flush_calls += 1
            super().flush()

    path = tmp_path / "flush.txt"
    stream = CountingStream()
    with LogPrint(path) as log:
        log.print("buffered", file=stream)
        assert stream.flush_calls == 0
        log.print("immediate", file=stream, flush=True)
        assert stream.flush_calls == 1
        assert path.read_text(encoding="utf-8") == "buffered\nimmediate\n"
        log.print("file flush", screen=False)
        log.flush()
        assert path.read_text(encoding="utf-8").endswith("file flush\n")


def test_close_is_idempotent_and_closed_operations_fail(tmp_path):
    log = LogPrint(tmp_path / "closed.txt")
    log.close()
    log.close()
    assert log.closed
    assert log.file_hnd.closed
    for operation in (log.print, log.flush, log.set_config, log.set_temp_config, log.__enter__):
        with pytest.raises(ValueError, match="closed"):
            operation()


def test_context_manager_closes_on_exception(tmp_path):
    with pytest.raises(RuntimeError, match="application error"):
        with LogPrint(tmp_path / "exception.txt") as log:
            raise RuntimeError("application error")
    assert log.closed
    assert log.file_hnd.closed


def test_screen_only_mode_is_explicit(capsys):
    with LogPrint(file=None) as log:
        log.print("screen only")
        assert log.file_hnd is None
        with pytest.raises(ValueError, match="no log file"):
            log.set_config(log_to_file=True)
    assert capsys.readouterr().out == "screen only\n"


@pytest.mark.parametrize("options", [{"write_mode": "r"}, {"print_header": "False"}])
def test_invalid_constructor_options_do_not_touch_file(tmp_path, options):
    path = tmp_path / "untouched.txt"
    path.write_text("keep", encoding="utf-8")
    with pytest.raises((TypeError, ValueError)):
        LogPrint(path, **options)
    assert path.read_text(encoding="utf-8") == "keep"


def test_redirected_stdout_is_resolved_at_call_time(tmp_path):
    target = io.StringIO()
    with LogPrint(tmp_path / "redirect.txt") as log:
        with contextlib.redirect_stdout(target):
            log.print("redirected")
    assert target.getvalue() == "redirected\n"


def test_shared_log_stream_is_not_written_twice(tmp_path):
    path = tmp_path / "same.txt"
    with LogPrint(path) as log:
        log.print("once", file=log.file_hnd)
    assert path.read_text(encoding="utf-8") == "once\n"


def test_write_errors_propagate(tmp_path):
    class BrokenStream:
        def write(self, message):
            raise OSError("destination failed")

    with LogPrint(tmp_path / "write-error.txt") as log:
        with pytest.raises(OSError, match="destination failed"):
            log.print("message", file=BrokenStream())


def test_threaded_messages_keep_both_destinations_identical(tmp_path):
    path = tmp_path / "threads.txt"
    target = io.StringIO()
    with LogPrint(path) as log:
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(lambda number: log.print(number, file=target), range(100)))
    output = target.getvalue()
    assert path.read_text(encoding="utf-8") == output
    assert sorted(map(int, output.splitlines())) == list(range(100))
