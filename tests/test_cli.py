"""Tests for core/cli.py's argument parsing (skipped automatically without PyQt6)."""

import pytest

pytest.importorskip("PyQt6")

from core.cli import build_arg_parser  # noqa: E402


def test_no_args_means_gui_mode():
    args = build_arg_parser().parse_args([])
    assert args.command is None


def test_start_with_overrides():
    args = build_arg_parser().parse_args(
        ["start", "--hostname", "myhost", "--port", "8080", "--no-sudo"]
    )
    assert args.command == "start"
    assert args.hostname == "myhost"
    assert args.port == 8080
    assert args.use_sudo is False


def test_start_default_sudo_is_none():
    args = build_arg_parser().parse_args(["start"])
    assert args.use_sudo is None


def test_simple_subcommands():
    for name in ("stop", "status", "version", "install-tailscale", "update-tailscale"):
        args = build_arg_parser().parse_args([name])
        assert args.command == name


def test_sudo_flags_are_mutually_exclusive():
    with pytest.raises(SystemExit):
        build_arg_parser().parse_args(["start", "--sudo", "--no-sudo"])
