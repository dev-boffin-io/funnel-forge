"""
Main window for Funnel-Forge.

A small PyQt6 GUI over Tailscale Funnel: configure hostname/port, start or
stop the funnel, watch live logs, and grab the resulting public URL.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.funnel_controller import FunnelController
from core.settings import IS_WINDOWS, load_settings, save_settings


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Funnel-Forge — Tailscale Funnel Manager")
        self.resize(720, 560)

        self.settings = load_settings()
        self.controller = FunnelController(self)
        self.controller.log_line.connect(self._append_log)
        self.controller.status_changed.connect(self._on_status_changed)
        self.controller.public_url_found.connect(self._on_public_url)
        self.controller.error_occurred.connect(self._on_error)

        self._build_ui()
        self._load_settings_into_ui()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # --- Configuration group ---
        config_box = QGroupBox("কনফিগারেশন")
        form = QFormLayout(config_box)

        self.hostname_input = QLineEdit()
        self.hostname_input.setPlaceholderText("e.g. boffin-io")
        form.addRow("Hostname:", self.hostname_input)

        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        form.addRow("Port:", self.port_input)

        self.socket_input = QLineEdit()
        form.addRow("Socket path:", self.socket_input)

        self.sudo_checkbox = QCheckBox("sudo ব্যবহার করুন")
        self.sudo_checkbox.setEnabled(not IS_WINDOWS)
        form.addRow("", self.sudo_checkbox)

        root.addWidget(config_box)

        # --- Controls row ---
        controls = QHBoxLayout()
        self.start_button = QPushButton("▶ Start Funnel")
        self.start_button.clicked.connect(self._on_start_clicked)
        self.stop_button = QPushButton("■ Stop Funnel")
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.stop_button.setEnabled(False)
        self.save_button = QPushButton("Settings সেভ করুন")
        self.save_button.clicked.connect(self._on_save_clicked)

        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        controls.addWidget(self.save_button)
        root.addLayout(controls)

        # --- Status row ---
        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Status:"))
        self.status_label = QLabel("বন্ধ আছে")
        self.status_label.setStyleSheet("color: #b00020; font-weight: bold;")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        root.addLayout(status_row)

        # --- Public URL row ---
        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("Public URL:"))
        self.url_label = QLabel("—")
        self.url_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        url_font = QFont()
        url_font.setBold(True)
        self.url_label.setFont(url_font)
        url_row.addWidget(self.url_label)
        url_row.addStretch()
        root.addLayout(url_row)

        # --- Log view ---
        root.addWidget(QLabel("Log:"))
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("monospace"))
        root.addWidget(self.log_view, stretch=1)

    def _load_settings_into_ui(self) -> None:
        self.hostname_input.setText(self.settings["hostname"])
        self.port_input.setValue(self.settings["port"])
        self.socket_input.setText(self.settings["socket_path"])
        self.sudo_checkbox.setChecked(self.settings["use_sudo"])

    def _collect_settings_from_ui(self) -> dict:
        return {
            "hostname": self.hostname_input.text().strip() or "boffin-io",
            "port": self.port_input.value(),
            "socket_path": self.socket_input.text().strip() or "/tmp/tailscaled.sock",
            "use_sudo": self.sudo_checkbox.isChecked(),
        }

    # ------------------------------------------------------------------ #
    # Slots
    # ------------------------------------------------------------------ #

    def _on_start_clicked(self) -> None:
        self.settings = self._collect_settings_from_ui()
        save_settings(self.settings)
        self.url_label.setText("—")
        self.log_view.clear()
        self.controller.start(self.settings)

    def _on_stop_clicked(self) -> None:
        self.controller.stop(self.settings)

    def _on_save_clicked(self) -> None:
        self.settings = self._collect_settings_from_ui()
        save_settings(self.settings)
        self._append_log("Settings সেভ হয়েছে।")

    def _on_status_changed(self, running: bool) -> None:
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        if running:
            self.status_label.setText("চালু আছে")
            self.status_label.setStyleSheet("color: #1b8a2f; font-weight: bold;")
        else:
            self.status_label.setText("বন্ধ আছে")
            self.status_label.setStyleSheet("color: #b00020; font-weight: bold;")

    def _on_public_url(self, url: str) -> None:
        self.url_label.setText(url)

    def _on_error(self, message: str) -> None:
        QMessageBox.critical(self, "Error", message)
        self._append_log(f"[ERROR] {message}")

    def _append_log(self, line: str) -> None:
        self.log_view.appendPlainText(line)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if self.controller.is_running():
            self.controller.stop(self.settings)
        event.accept()
