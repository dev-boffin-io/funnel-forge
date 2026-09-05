#!/usr/bin/env python3
"""
Funnel-Forge — PyQt6 GUI (and CLI) for managing a Tailscale Funnel.

Run with no arguments for the GUI: python main.py
Run with a subcommand for CLI mode, e.g.: python main.py start --port 3000
See `python main.py --help` for all subcommands.
"""

import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from core.cli import maybe_run_cli
from core.logger import get_logger, setup_logging
from ui.main_window import MainWindow


def main() -> int:
    setup_logging()
    logger = get_logger("main")

    cli_exit_code = maybe_run_cli()
    if cli_exit_code is not None:
        logger.info("Funnel-Forge CLI command finished with code %s.", cli_exit_code)
        return cli_exit_code

    logger.info("Funnel-Forge starting up (GUI).")
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
