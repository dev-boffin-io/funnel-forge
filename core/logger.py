"""
Rotating file logging for Funnel-Forge.

The GUI's on-screen log panels are cleared whenever the app restarts, so
this also writes everything to a rotating log file on disk - the thing
you actually want when something goes wrong after the window is closed.
"""

import logging
import tempfile
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(tempfile.gettempdir()) / "funnel-forge-logs"
LOG_FILE = LOG_DIR / "funnel-forge.log"

MAX_BYTES = 1_000_000  # ~1 MB per file
BACKUP_COUNT = 3

_configured = False


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root 'funnel_forge' logger. Safe to call more than once."""
    global _configured
    if _configured:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("funnel_forge")
    logger.setLevel(level)

    handler = RotatingFileHandler(
        LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    _configured = True
    logger.info("Logging started. Log file: %s", LOG_FILE)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"funnel_forge.{name}")
