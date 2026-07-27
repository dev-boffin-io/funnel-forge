#!/usr/bin/env python3
"""
Funnel-Forge — PyQt6 GUI for managing a Tailscale Funnel.

Run with: python main.py
"""

import sys

from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Funnel-Forge")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
