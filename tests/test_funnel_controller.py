"""
Tests for the non-Qt-event-loop parts of core/funnel_controller.py.

These only exercise static/pure logic (binary resolution, URL parsing,
PID liveness) - nothing here needs a running QApplication event loop.
Skipped automatically wherever PyQt6 isn't installed (e.g. CI lint-only
jobs, or this sandbox).
"""

import os

import pytest

pytest.importorskip("PyQt6")

from core.funnel_controller import URL_PATTERN, FunnelController, _is_pid_alive  # noqa: E402


def test_url_pattern_finds_a_funnel_url():
    line = "Available on the internet: https://share-forge.example.ts.net/"
    match = URL_PATTERN.search(line)
    assert match is not None
    assert match.group(0).startswith("https://share-forge.example.ts.net")


def test_url_pattern_no_match_on_plain_log_line():
    assert URL_PATTERN.search("Starting Tailscale daemon...") is None


def test_validate_manual_rejects_missing_path(tmp_path):
    missing = tmp_path / "does-not-exist"
    assert FunnelController._validate_manual(str(missing)) is None


def test_validate_manual_accepts_executable_file(tmp_path):
    script = tmp_path / "fake-tailscale"
    script.write_text("#!/bin/sh\necho hi\n")
    script.chmod(0o755)
    assert FunnelController._validate_manual(str(script)) == str(script)


@pytest.mark.skipif(
    os.name == "nt",
    reason="Windows has no POSIX execute-permission bit; os.access(X_OK) "
    "returns True for any existing file regardless of chmod there.",
)
def test_validate_manual_rejects_non_executable_file(tmp_path):
    script = tmp_path / "not-executable"
    script.write_text("just a file")
    script.chmod(0o644)
    assert FunnelController._validate_manual(str(script)) is None


def test_resolve_binary_finds_via_extra_dirs(monkeypatch, tmp_path):
    import core.funnel_controller as fc

    monkeypatch.setattr(fc.shutil, "which", lambda name: None)
    monkeypatch.setattr(fc, "EXTRA_BINARY_DIRS", [str(tmp_path)])

    fake_bin = tmp_path / "tailscale"
    fake_bin.write_text("#!/bin/sh\n")
    fake_bin.chmod(0o755)

    assert FunnelController._resolve_binary("tailscale") == str(fake_bin)


def test_resolve_binary_returns_none_when_not_found(monkeypatch, tmp_path):
    import core.funnel_controller as fc

    monkeypatch.setattr(fc.shutil, "which", lambda name: None)
    monkeypatch.setattr(fc, "EXTRA_BINARY_DIRS", [str(tmp_path)])

    assert FunnelController._resolve_binary("tailscale") is None


def test_is_pid_alive_true_for_current_process():
    assert _is_pid_alive(os.getpid()) is True


def test_is_pid_alive_false_for_bogus_pid():
    # A pid this large should not exist on any real system.
    assert _is_pid_alive(2**30) is False


def test_is_pid_alive_false_for_zero_or_negative():
    assert _is_pid_alive(0) is False
    assert _is_pid_alive(-1) is False
