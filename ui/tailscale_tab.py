"""
Tailscale management tab.

Lets the user install Tailscale, check its version, trigger an update,
enable automatic update checks on startup, and choose between
auto-detected or manually specified binary paths for tailscale/tailscaled.
"""

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from core.funnel_controller import FunnelController

LOG_FONT_SIZE = 12
SECTION_FONT_SIZE = 14


class TailscaleTab(QWidget):
    def __init__(self, controller: FunnelController, get_settings, on_settings_changed):
        super().__init__()
        self.controller = controller
        self._get_settings = get_settings
        self._on_settings_changed = on_settings_changed

        self.controller.tool_log.connect(self._append_log)
        self.controller.tool_busy_changed.connect(self._on_busy_changed)
        self.controller.version_result.connect(self._on_version_result)

        self._build_ui()
        self._load_from_settings()
        self.refresh_version()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # --- Version / install / update ---
        version_box = QGroupBox("Tailscale binary")
        version_box.setFont(self._section_font())
        vbox = QVBoxLayout(version_box)

        version_row = QHBoxLayout()
        version_row.addWidget(QLabel("Installed version:"))
        self.version_label = QLabel("Checking...")
        version_row.addWidget(self.version_label)
        version_row.addStretch()
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_version)
        version_row.addWidget(self.refresh_button)
        vbox.addLayout(version_row)

        button_row = QHBoxLayout()
        self.install_button = QPushButton("Install Tailscale")
        self.install_button.setMinimumHeight(38)
        self.install_button.clicked.connect(self._on_install_clicked)
        button_row.addWidget(self.install_button)

        self.update_button = QPushButton("Check & Update")
        self.update_button.setMinimumHeight(38)
        self.update_button.clicked.connect(self._on_update_clicked)
        button_row.addWidget(self.update_button)

        self.manual_upgrade_button = QPushButton("Manual Upgrade (re-run installer)")
        self.manual_upgrade_button.setMinimumHeight(38)
        self.manual_upgrade_button.clicked.connect(self._on_install_clicked)
        button_row.addWidget(self.manual_upgrade_button)
        vbox.addLayout(button_row)

        self.auto_update_checkbox = QCheckBox("Automatically check for updates on startup")
        self.auto_update_checkbox.stateChanged.connect(self._on_auto_update_toggled)
        vbox.addWidget(self.auto_update_checkbox)

        root.addWidget(version_box)

        # --- Binary path ---
        path_box = QGroupBox("Binary path")
        path_box.setFont(self._section_font())
        form = QFormLayout(path_box)
        form.setVerticalSpacing(10)

        radio_row = QHBoxLayout()
        self.auto_radio = QRadioButton("Auto-detect")
        self.manual_radio = QRadioButton("Manual")
        self.auto_radio.toggled.connect(self._on_path_mode_changed)
        radio_row.addWidget(self.auto_radio)
        radio_row.addWidget(self.manual_radio)
        radio_row.addStretch()
        form.addRow("Path mode:", radio_row)

        self.tailscale_path_input = QLineEdit()
        self.tailscale_path_browse = QPushButton("Browse...")
        self.tailscale_path_browse.clicked.connect(
            lambda: self._browse_for(self.tailscale_path_input)
        )
        ts_row = QHBoxLayout()
        ts_row.addWidget(self.tailscale_path_input)
        ts_row.addWidget(self.tailscale_path_browse)
        form.addRow("tailscale path:", ts_row)

        self.tailscaled_path_input = QLineEdit()
        self.tailscaled_path_browse = QPushButton("Browse...")
        self.tailscaled_path_browse.clicked.connect(
            lambda: self._browse_for(self.tailscaled_path_input)
        )
        tsd_row = QHBoxLayout()
        tsd_row.addWidget(self.tailscaled_path_input)
        tsd_row.addWidget(self.tailscaled_path_browse)
        form.addRow("tailscaled path:", tsd_row)

        self.tailscale_path_input.editingFinished.connect(self._save_path_fields)
        self.tailscaled_path_input.editingFinished.connect(self._save_path_fields)

        root.addWidget(path_box)

        # --- Log ---
        log_label = QLabel("Install / update log:")
        log_label.setFont(self._section_font())
        root.addWidget(log_label)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        log_font = QFont("monospace")
        log_font.setPointSize(LOG_FONT_SIZE)
        self.log_view.setFont(log_font)
        root.addWidget(self.log_view, stretch=1)

    @staticmethod
    def _section_font() -> QFont:
        font = QFont()
        font.setPointSize(SECTION_FONT_SIZE)
        font.setBold(True)
        return font

    # ------------------------------------------------------------------ #
    # Settings glue
    # ------------------------------------------------------------------ #

    def _load_from_settings(self) -> None:
        settings = self._get_settings()
        manual = settings.get("path_mode") == "manual"
        self.manual_radio.setChecked(manual)
        self.auto_radio.setChecked(not manual)
        self.tailscale_path_input.setText(settings.get("tailscale_path", ""))
        self.tailscaled_path_input.setText(settings.get("tailscaled_path", ""))
        self.auto_update_checkbox.setChecked(settings.get("auto_update_check", False))
        self._update_path_fields_enabled()

    def _update_path_fields_enabled(self) -> None:
        manual = self.manual_radio.isChecked()
        for widget in (
            self.tailscale_path_input,
            self.tailscale_path_browse,
            self.tailscaled_path_input,
            self.tailscaled_path_browse,
        ):
            widget.setEnabled(manual)

    def _browse_for(self, line_edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select binary")
        if path:
            line_edit.setText(path)
            self._save_path_fields()

    def _on_path_mode_changed(self, _checked: bool) -> None:
        self._update_path_fields_enabled()
        settings = self._get_settings()
        settings["path_mode"] = "manual" if self.manual_radio.isChecked() else "auto"
        self._on_settings_changed(settings)
        self.refresh_version()

    def _save_path_fields(self) -> None:
        settings = self._get_settings()
        settings["tailscale_path"] = self.tailscale_path_input.text().strip()
        settings["tailscaled_path"] = self.tailscaled_path_input.text().strip()
        self._on_settings_changed(settings)
        self.refresh_version()

    def _on_auto_update_toggled(self, _state: int) -> None:
        settings = self._get_settings()
        settings["auto_update_check"] = self.auto_update_checkbox.isChecked()
        self._on_settings_changed(settings)

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #

    def refresh_version(self) -> None:
        self.version_label.setText("Checking...")
        self.controller.check_version(self._get_settings())

    def _on_install_clicked(self) -> None:
        self.log_view.clear()
        self.controller.install_tailscale()

    def _on_update_clicked(self) -> None:
        self.log_view.clear()
        self.controller.update_tailscale(self._get_settings())

    def maybe_auto_update(self) -> None:
        if self.auto_update_checkbox.isChecked():
            self._append_log("Auto-update check enabled - checking now...")
            self.controller.update_tailscale(self._get_settings())

    # ------------------------------------------------------------------ #
    # Signal handlers
    # ------------------------------------------------------------------ #

    def _append_log(self, line: str) -> None:
        self.log_view.appendPlainText(line)

    def _on_busy_changed(self, busy: bool) -> None:
        for button in (self.install_button, self.update_button, self.manual_upgrade_button):
            button.setEnabled(not busy)
        if not busy:
            self.refresh_version()

    def _on_version_result(self, text: str) -> None:
        self.version_label.setText(text)
