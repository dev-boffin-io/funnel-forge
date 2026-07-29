"""Tests for core/settings.py - no PyQt6 needed, pure file I/O logic."""

import json

import pytest

from core import settings as settings_module


@pytest.fixture(autouse=True)
def isolated_settings_file(tmp_path, monkeypatch):
    """Point SETTINGS_FILE at a throwaway path so tests never touch the real one."""
    fake_path = tmp_path / "settings.json"
    monkeypatch.setattr(settings_module, "SETTINGS_FILE", fake_path)
    return fake_path


def test_load_settings_returns_defaults_when_no_file(isolated_settings_file):
    result = settings_module.load_settings()
    assert result == settings_module.DEFAULT_SETTINGS
    assert not isolated_settings_file.exists()


def test_save_then_load_round_trips(isolated_settings_file):
    custom = dict(settings_module.DEFAULT_SETTINGS)
    custom["hostname"] = "my-host"
    custom["port"] = 8080

    settings_module.save_settings(custom)
    loaded = settings_module.load_settings()

    assert loaded["hostname"] == "my-host"
    assert loaded["port"] == 8080


def test_load_settings_fills_in_missing_keys(isolated_settings_file):
    # Simulate an older settings.json missing a newer key.
    partial = {"hostname": "partial-host"}
    isolated_settings_file.write_text(json.dumps(partial), encoding="utf-8")

    loaded = settings_module.load_settings()

    assert loaded["hostname"] == "partial-host"
    assert loaded["port"] == settings_module.DEFAULT_SETTINGS["port"]
    assert loaded["path_mode"] == settings_module.DEFAULT_SETTINGS["path_mode"]


def test_load_settings_recovers_from_corrupt_json(isolated_settings_file):
    isolated_settings_file.write_text("{not valid json", encoding="utf-8")

    loaded = settings_module.load_settings()

    assert loaded == settings_module.DEFAULT_SETTINGS
