"""
Settings persistence for Funnel-Forge.

Stores user-configurable values (hostname, port, socket path, sudo usage)
in a local settings.json file next to the application, so the GUI
remembers the last-used configuration between runs.
"""

import json
import platform
from pathlib import Path
from typing import Any, Dict

APP_DIR = Path(__file__).resolve().parent.parent
SETTINGS_FILE = APP_DIR / "settings.json"

IS_WINDOWS = platform.system() == "Windows"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "hostname": "boffin-io",
    "port": 3000,
    "socket_path": "/tmp/tailscaled.sock",
    "use_sudo": not IS_WINDOWS,
    # "auto" = search PATH + common install dirs; "manual" = use the two
    # paths below exactly as given.
    "path_mode": "auto",
    "tailscale_path": "",
    "tailscaled_path": "",
    # If true, check for a Tailscale update once each time the app starts.
    "auto_update_check": False,
}


def load_settings() -> Dict[str, Any]:
    """Load settings.json, falling back to defaults for any missing keys."""
    settings = DEFAULT_SETTINGS.copy()
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                settings.update(saved)
        except (json.JSONDecodeError, OSError):
            # Corrupt or unreadable settings file - fall back to defaults.
            pass
    return settings


def save_settings(settings: Dict[str, Any]) -> None:
    """Persist settings to settings.json."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
    except OSError as exc:
        raise RuntimeError(f"Could not save settings: {exc}") from exc
