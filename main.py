#!/usr/bin/env python3
"""
Funnel-Forge — PyQt6 GUI for managing a Tailscale Funnel.

Run with: python main.py
"""

import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from core.logger import get_logger, setup_logging
from ui.main_window import MainWindow


def main() -> int:
    setup_logging()
    logger = get_logger("main")
    logger.info("Funnel-Forge starting up.")

    app = QApplication(sys.argv)
    app.setApplicationName("Funnel-Forge")
    app.setFont(QFont("", 13))
    window = MainWindow()
    window.show()
    exit_code = app.exec()

    logger.info("Funnel-Forge exiting with code %s.", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
