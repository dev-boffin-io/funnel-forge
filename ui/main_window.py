"""
Main window for Funnel-Forge.

Two tabs:
- "Funnel": configure hostname/port, start/stop, live log, public URL.
- "Tailscale": install/update Tailscale itself, check its version, and
  choose between auto-detected or manually specified binary paths.

Closing the window does NOT stop a running Funnel - it keeps running in
the background (the process is detached from the GUI), matching how the
original shell-script workflow left it running in a terminal. The user
can always come back and press Stop, or close it from the Tailscale tab
tools if needed.
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
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.funnel_controller import FunnelController
from core.settings import IS_WINDOWS, load_settings, save_settings
from ui.tailscale_tab import TailscaleTab

BASE_FONT_SIZE = 13
LOG_FONT_SIZE = 12
BUTTON_FONT_SIZE = 13


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Funnel-Forge — Tailscale Funnel Manager")
        self.resize(1100, 820)
        self.setMinimumSize(900, 650)

        self.settings = load_settings()
        self.controller = FunnelController(self)
        self.controller.log_line.connect(self._append_log)
        self.controller.status_changed.connect(self._on_status_changed)
        self.controller.public_url_found.connect(self._on_public_url)
        self.controller.error_occurred.connect(self._on_error)

        self._build_ui()
        self._load_settings_into_ui()

        self.controller.detect_existing_session()
        self.tailscale_tab.maybe_auto_update()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        tabs = QTabWidget(self)
        self.setCentralWidget(tabs)

        funnel_page = QWidget()
        self._build_funnel_tab(funnel_page)
        tabs.addTab(funnel_page, "Funnel")

        self.tailscale_tab = TailscaleTab(
            self.controller, self._collect_settings_from_ui, self._apply_settings_from_tab
        )
        tabs.addTab(self.tailscale_tab, "Tailscale")

    def _build_funnel_tab(self, central: QWidget) -> None:
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        base_font = QFont()
        base_font.setPointSize(BASE_FONT_SIZE)
        self.setFont(base_font)

        # --- Configuration group ---
        config_box = QGroupBox("Configuration")
        config_box.setFont(self._section_font())
        form = QFormLayout(config_box)
        form.setVerticalSpacing(12)
        form.setHorizontalSpacing(16)

        self.hostname_input = QLineEdit()
        self.hostname_input.setPlaceholderText("e.g. boffin-io")
        self.hostname_input.setMinimumHeight(34)
        form.addRow("Hostname:", self.hostname_input)

        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setMinimumHeight(34)
        form.addRow("Port:", self.port_input)

        self.socket_input = QLineEdit()
        self.socket_input.setMinimumHeight(34)
        form.addRow("Socket path:", self.socket_input)

        self.sudo_checkbox = QCheckBox("Use sudo")
        self.sudo_checkbox.setEnabled(not IS_WINDOWS)
        form.addRow("", self.sudo_checkbox)

        root.addWidget(config_box)

        # --- Controls row ---
        controls = QHBoxLayout()
        controls.setSpacing(12)
        self.start_button = QPushButton("▶  Start Funnel")
        self.start_button.setMinimumHeight(42)
        self.start_button.setFont(self._button_font())
        self.start_button.clicked.connect(self._on_start_clicked)

        self.stop_button = QPushButton("■  Stop Funnel")
        self.stop_button.setMinimumHeight(42)
        self.stop_button.setFont(self._button_font())
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.stop_button.setEnabled(False)

        self.save_button = QPushButton("Save Settings")
        self.save_button.setMinimumHeight(42)
        self.save_button.setFont(self._button_font())
        self.save_button.clicked.connect(self._on_save_clicked)

        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        controls.addWidget(self.save_button)
        root.addLayout(controls)

        # --- Status row ---
        status_row = QHBoxLayout()
        status_label_caption = QLabel("Status:")
        status_label_caption.setFont(self._section_font())
        status_row.addWidget(status_label_caption)
        self.status_label = QLabel("Stopped")
        self.status_label.setFont(self._section_font())
        self.status_label.setStyleSheet("color: #d94141; font-weight: bold;")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        root.addLayout(status_row)

        # --- Public URL row ---
        url_row = QHBoxLayout()
        url_caption = QLabel("Public URL:")
        url_caption.setFont(self._section_font())
        url_row.addWidget(url_caption)
        self.url_label = QLabel("—")
        self.url_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.url_label.setFont(self._section_font())
        url_row.addWidget(self.url_label)
        url_row.addStretch()
        root.addLayout(url_row)

        # --- Log view ---
        log_caption = QLabel("Log:")
        log_caption.setFont(self._section_font())
        root.addWidget(log_caption)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        log_font = QFont("monospace")
        log_font.setPointSize(LOG_FONT_SIZE)
        self.log_view.setFont(log_font)
        root.addWidget(self.log_view, stretch=1)

    @staticmethod
    def _section_font() -> QFont:
        font = QFont()
        font.setPointSize(BASE_FONT_SIZE + 1)
        font.setBold(True)
        return font

    @staticmethod
    def _button_font() -> QFont:
        font = QFont()
        font.setPointSize(BUTTON_FONT_SIZE)
        font.setBold(True)
        return font

    def _load_settings_into_ui(self) -> None:
        self.hostname_input.setText(self.settings["hostname"])
        self.port_input.setValue(self.settings["port"])
        self.socket_input.setText(self.settings["socket_path"])
        self.sudo_checkbox.setChecked(self.settings["use_sudo"])

    def _collect_settings_from_ui(self) -> dict:
        merged = dict(self.settings)
        merged.update(
            {
                "hostname": self.hostname_input.text().strip() or "boffin-io",
                "port": self.port_input.value(),
                "socket_path": self.socket_input.text().strip() or "/tmp/tailscaled.sock",
                "use_sudo": self.sudo_checkbox.isChecked(),
            }
        )
        return merged

    def _apply_settings_from_tab(self, settings: dict) -> None:
        """Called by the Tailscale tab when it changes a settings value."""
        self.settings = settings
        save_settings(self.settings)

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
        self._append_log("Settings saved.")

    def _on_status_changed(self, running: bool) -> None:
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        if running:
            self.status_label.setText("Running")
            self.status_label.setStyleSheet("color: #1b8a2f; font-weight: bold;")
        else:
            self.status_label.setText("Stopped")
            self.status_label.setStyleSheet("color: #d94141; font-weight: bold;")

    def _on_public_url(self, url: str) -> None:
        self.url_label.setText(url)

    def _on_error(self, message: str) -> None:
        QMessageBox.critical(self, "Error", message)
        self._append_log(f"[ERROR] {message}")

    def _append_log(self, line: str) -> None:
        self.log_view.appendPlainText(line)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        """Closing the window leaves a running Funnel alone (see module docstring)."""
        if self.controller.is_running():
            QMessageBox.information(
                self,
                "Funnel-Forge",
                "The Funnel keeps running in the background after you close this "
                "window. Reopen the app and press Stop Funnel when you want to "
                "shut it down.",
            )
        event.accept()
