"""
FunnelController: manages the Tailscale daemon + funnel lifecycle.

Replaces the original start-funnel.sh / stop-funnel.sh shell scripts with
QProcess-driven, non-blocking process management so the PyQt6 GUI never
freezes while Tailscale starts up, connects, or streams funnel logs.
"""

import re
import shutil
from typing import Dict, List, Optional

from PyQt6.QtCore import QObject, QProcess, QTimer, pyqtSignal

from core.settings import IS_WINDOWS

URL_PATTERN = re.compile(r"https://[^\s]+")


class FunnelController(QObject):
    """Drives tailscaled / tailscale processes and reports status + logs."""

    log_line = pyqtSignal(str)
    status_changed = pyqtSignal(bool)          # True = running
    public_url_found = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._daemon_process: Optional[QProcess] = None
        self._funnel_process: Optional[QProcess] = None
        self._running = False

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def is_running(self) -> bool:
        return self._running

    def start(self, settings: Dict) -> None:
        """Kick off: cleanup -> tailscaled -> tailscale up -> tailscale funnel."""
        if self._running:
            self.log_line.emit("ইতিমধ্যে চালু আছে।")
            return

        if not self._binary_available("tailscale") or not self._binary_available("tailscaled"):
            self.error_occurred.emit(
                "tailscale / tailscaled বাইনারি খুঁজে পাওয়া যায়নি। ইনস্টল আছে কিনা এবং PATH-এ আছে কিনা যাচাই করুন।"
            )
            return

        self._cleanup_sync(settings)

        self.log_line.emit("Tailscale daemon চালু করা হচ্ছে...")
        self._daemon_process = QProcess(self)
        self._daemon_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._daemon_process.readyReadStandardOutput.connect(
            lambda: self._emit_output(self._daemon_process)
        )
        daemon_cmd, daemon_args = self._wrap_sudo(
            settings,
            [
                "tailscaled",
                "--tun=userspace-networking",
                f"--socket={settings['socket_path']}",
            ],
        )
        self._daemon_process.start(daemon_cmd, daemon_args)

        # Give the daemon a moment to create its socket before "up".
        QTimer.singleShot(3000, lambda: self._run_up(settings))

    def stop(self, settings: Dict) -> None:
        """Terminate funnel + daemon processes and clean up the socket."""
        if self._funnel_process is not None:
            self._funnel_process.kill()
            self._funnel_process = None

        self.log_line.emit("Tailscale প্রসেসসমূহ বন্ধ করা হচ্ছে...")
        self._run_blocking(self._wrap_sudo(settings, ["pkill", "tailscale"]))
        self._run_blocking(self._wrap_sudo(settings, ["pkill", "tailscaled"]))
        self._remove_socket(settings)

        if self._daemon_process is not None:
            self._daemon_process.kill()
            self._daemon_process = None

        self._set_running(False)
        self.log_line.emit("Tailscale daemon ও Funnel সফলভাবে বন্ধ হয়েছে।")

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _run_up(self, settings: Dict) -> None:
        self.log_line.emit("নেটওয়ার্কে সংযোগ করা হচ্ছে (tailscale up)...")
        cmd, args = self._wrap_sudo(
            settings,
            [
                "tailscale",
                f"--socket={settings['socket_path']}",
                "up",
                f"--hostname={settings['hostname']}",
            ],
        )
        self._run_blocking((cmd, args))
        self._run_funnel(settings)

    def _run_funnel(self, settings: Dict) -> None:
        port = settings["port"]
        self.log_line.emit(f"পোর্ট {port}-এর জন্য Funnel চালু করা হচ্ছে...")
        self._funnel_process = QProcess(self)
        self._funnel_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._funnel_process.readyReadStandardOutput.connect(
            lambda: self._emit_output(self._funnel_process, watch_url=True)
        )
        self._funnel_process.finished.connect(lambda *_: self._set_running(False))
        cmd, args = self._wrap_sudo(
            settings,
            ["tailscale", f"--socket={settings['socket_path']}", "funnel", str(port)],
        )
        self._funnel_process.start(cmd, args)
        self._set_running(True)

    def _cleanup_sync(self, settings: Dict) -> None:
        self._run_blocking(self._wrap_sudo(settings, ["pkill", "tailscaled"]))
        self._remove_socket(settings)

    def _remove_socket(self, settings: Dict) -> None:
        if IS_WINDOWS:
            return
        self._run_blocking(self._wrap_sudo(settings, ["rm", "-f", settings["socket_path"]]))

    def _wrap_sudo(self, settings: Dict, args: List[str]) -> "tuple[str, List[str]]":
        if settings.get("use_sudo") and not IS_WINDOWS:
            return "sudo", args
        return args[0], args[1:]

    def _run_blocking(self, cmd_args: "tuple[str, List[str]]") -> None:
        """Run a short cleanup command synchronously and swallow failures."""
        cmd, args = cmd_args
        proc = QProcess()
        proc.start(cmd, args)
        proc.waitForFinished(5000)

    def _emit_output(self, process: Optional[QProcess], watch_url: bool = False) -> None:
        if process is None:
            return
        data = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
        for line in data.splitlines():
            if not line.strip():
                continue
            self.log_line.emit(line)
            if watch_url:
                match = URL_PATTERN.search(line)
                if match:
                    self.public_url_found.emit(match.group(0))

    def _set_running(self, running: bool) -> None:
        self._running = running
        self.status_changed.emit(running)

    @staticmethod
    def _binary_available(name: str) -> bool:
        return shutil.which(name) is not None
