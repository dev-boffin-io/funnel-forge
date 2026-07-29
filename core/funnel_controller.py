"""
FunnelController: manages the Tailscale daemon + funnel lifecycle.

Two things drive the design here:

1. The funnel/daemon processes are launched *detached* (via
   QProcess.startDetached, with their output redirected to log files on
   disk) so that closing the GUI does NOT kill them - the tunnel keeps
   serving traffic in the background, the same way the original
   start-funnel.sh script left it running in a terminal. The GUI tails
   the log files with a timer instead of reading a live QProcess pipe.

2. Tailscale binary discovery, install, and update also live here, so
   the "Tailscale" management tab can install/update Tailscale itself
   and let the user pick between auto-detected or manually specified
   binary paths.
"""

import os
import re
import shlex
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import QObject, QProcess, QTimer, pyqtSignal

from core.logger import get_logger
from core.settings import IS_WINDOWS

logger = get_logger("funnel_controller")

URL_PATTERN = re.compile(r"https://[^\s]+")

# tailscaled in particular is very commonly installed under /usr/sbin or
# /usr/local/sbin, directories that are NOT on a normal (non-root) user's
# PATH. shutil.which() alone therefore misses it even when it's installed
# and runnable with sudo, so we also probe these locations explicitly.
EXTRA_BINARY_DIRS = [
    "/usr/sbin",
    "/usr/local/sbin",
    "/sbin",
    "/usr/bin",
    "/usr/local/bin",
]

_TMP = Path(tempfile.gettempdir())
DAEMON_LOG_FILE = _TMP / "funnel-forge-daemon.log"
FUNNEL_LOG_FILE = _TMP / "funnel-forge-funnel.log"

INSTALL_SCRIPT_URL = "https://tailscale.com/install.sh"


def _is_pid_alive(pid: int) -> bool:
    if pid is None or pid <= 0:
        return False
    if IS_WINDOWS:
        try:
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid
            )
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
    except Exception:
        return False


class FunnelController(QObject):
    """Drives tailscaled / tailscale processes and reports status + logs."""

    log_line = pyqtSignal(str)
    status_changed = pyqtSignal(bool)          # True = running
    public_url_found = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    # Tailscale install/update/version management (separate channel so it
    # doesn't mix into the funnel log view).
    tool_log = pyqtSignal(str)
    version_result = pyqtSignal(str)
    tool_busy_changed = pyqtSignal(bool)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._funnel_pid: Optional[int] = None
        self._running = False
        self._tailscale_bin: Optional[str] = None
        self._tailscaled_bin: Optional[str] = None

        self._tail_timer = QTimer(self)
        self._tail_timer.setInterval(700)
        self._tail_timer.timeout.connect(self._poll_logs)
        self._daemon_offset = 0
        self._funnel_offset = 0

        self._tool_process: Optional[QProcess] = None

    # ------------------------------------------------------------------ #
    # Startup: detect a funnel that's already running from a prior session
    # ------------------------------------------------------------------ #

    def detect_existing_session(self) -> None:
        """Called once at app startup to notice an already-running funnel."""
        proc = QProcess()
        proc.start("pgrep", ["-f", "tailscale .*funnel"])
        proc.waitForFinished(2000)
        output = bytes(proc.readAllStandardOutput()).decode(errors="replace").strip()
        pids = [int(p) for p in output.splitlines() if p.strip().isdigit()]
        if pids and _is_pid_alive(pids[0]):
            self._funnel_pid = pids[0]
            self._daemon_offset = self._file_size(DAEMON_LOG_FILE)
            self._funnel_offset = self._file_size(FUNNEL_LOG_FILE)
            self.log_line.emit("Detected a Funnel already running from a previous session.")
            self._set_running(True)
            self._tail_timer.start()

    # ------------------------------------------------------------------ #
    # Public API - funnel lifecycle
    # ------------------------------------------------------------------ #

    def is_running(self) -> bool:
        return self._running

    def start(self, settings: Dict) -> None:
        """Kick off: cleanup -> tailscaled -> tailscale up -> tailscale funnel."""
        if self._running:
            self.log_line.emit("Already running.")
            return

        if settings.get("use_sudo") and not IS_WINDOWS and not self._sudo_is_passwordless():
            logger.warning("Passwordless sudo is not available; refusing to start.")
            self.error_occurred.emit(
                "'sudo' requires a password in this environment, but Funnel-Forge "
                "runs commands in the background where it can't prompt for one. "
                "Either configure passwordless sudo for tailscale/tailscaled, or "
                "uncheck 'Use sudo' if you don't need it."
            )
            return

        self._resolve_paths(settings)
        if not self._tailscale_bin or not self._tailscaled_bin:
            missing = []
            if not self._tailscale_bin:
                missing.append("tailscale")
            if not self._tailscaled_bin:
                missing.append("tailscaled")
            logger.warning("Missing binaries: %s", ", ".join(missing))
            self.error_occurred.emit(
                "Could not find: " + ", ".join(missing) + ". "
                "Install Tailscale from the Tailscale tab, or set a manual "
                "binary path there."
            )
            return

        logger.info(
            "Starting Funnel (hostname=%s, port=%s).",
            settings.get("hostname"),
            settings.get("port"),
        )
        self._cleanup_sync(settings)
        self._daemon_offset = 0
        self._funnel_offset = 0
        for log_file in (DAEMON_LOG_FILE, FUNNEL_LOG_FILE):
            try:
                log_file.write_text("")
            except OSError:
                pass

        self.log_line.emit("Starting Tailscale daemon...")
        daemon_cmd = self._wrap_sudo(
            settings,
            [
                self._tailscaled_bin,
                "--tun=userspace-networking",
                f"--socket={settings['socket_path']}",
            ],
        )
        self._start_detached_redirected(daemon_cmd, DAEMON_LOG_FILE)

        # Give the daemon a moment to create its socket before "up".
        QTimer.singleShot(3000, lambda: self._run_up(settings))

    def stop(self, settings: Dict) -> None:
        """Terminate funnel + daemon processes and clean up the socket."""
        logger.info("Stopping Funnel.")
        self.log_line.emit("Stopping Tailscale processes...")
        self._run_blocking(self._wrap_sudo(settings, ["pkill", "tailscale"]))
        self._run_blocking(self._wrap_sudo(settings, ["pkill", "tailscaled"]))
        self._remove_socket(settings)

        self._funnel_pid = None
        self._tail_timer.stop()
        self._set_running(False)
        self.log_line.emit("Tailscale daemon and Funnel stopped successfully.")

    # ------------------------------------------------------------------ #
    # Public API - Tailscale install / update / version
    # ------------------------------------------------------------------ #

    def check_version(self, settings: Dict) -> None:
        self._resolve_paths(settings)
        if not self._tailscale_bin:
            self.version_result.emit("Not installed")
            return
        proc = QProcess()
        proc.start(self._tailscale_bin, ["version"])
        proc.waitForFinished(4000)
        output = bytes(proc.readAllStandardOutput()).decode(errors="replace").strip()
        first_line = output.splitlines()[0] if output else "Unknown"
        self.version_result.emit(first_line)

    def install_tailscale(self) -> None:
        """Run the official install script (also used for a full reinstall/upgrade)."""
        if self._tool_process is not None:
            self.tool_log.emit("A tool operation is already running.")
            return
        self.tool_log.emit(f"Running install script from {INSTALL_SCRIPT_URL} ...")
        self.tool_busy_changed.emit(True)
        cmd = f"curl -fsSL {shlex.quote(INSTALL_SCRIPT_URL)} | sh"
        self._tool_process = QProcess(self)
        self._tool_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._tool_process.readyReadStandardOutput.connect(self._emit_tool_output)
        self._tool_process.finished.connect(self._on_tool_finished)
        self._tool_process.start("bash", ["-c", cmd])

    def update_tailscale(self, settings: Dict) -> None:
        """Run `tailscale update` to self-update to the latest version."""
        if self._tool_process is not None:
            self.tool_log.emit("A tool operation is already running.")
            return
        self._resolve_paths(settings)
        if not self._tailscale_bin:
            self.tool_log.emit("tailscale binary not found - install it first.")
            return
        self.tool_log.emit("Checking for updates...")
        self.tool_busy_changed.emit(True)
        cmd, args = self._wrap_sudo(settings, [self._tailscale_bin, "update", "--yes"])
        self._tool_process = QProcess(self)
        self._tool_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._tool_process.readyReadStandardOutput.connect(self._emit_tool_output)
        self._tool_process.finished.connect(self._on_tool_finished)
        self._tool_process.start(cmd, args)

    def resolved_paths(self, settings: Dict) -> Tuple[Optional[str], Optional[str]]:
        """Return the (tailscale, tailscaled) paths that would currently be used."""
        self._resolve_paths(settings)
        return self._tailscale_bin, self._tailscaled_bin

    # ------------------------------------------------------------------ #
    # Internal helpers - funnel lifecycle
    # ------------------------------------------------------------------ #

    def _run_up(self, settings: Dict) -> None:
        self.log_line.emit("Connecting to the network (tailscale up)...")
        cmd, args = self._wrap_sudo(
            settings,
            [
                self._tailscale_bin,
                f"--socket={settings['socket_path']}",
                "up",
                f"--hostname={settings['hostname']}",
            ],
        )
        self._run_blocking((cmd, args))
        self._run_funnel(settings)

    def _run_funnel(self, settings: Dict) -> None:
        port = settings["port"]
        self.log_line.emit(f"Starting Funnel on port {port}...")
        cmd = self._wrap_sudo(
            settings,
            [self._tailscale_bin, f"--socket={settings['socket_path']}", "funnel", str(port)],
        )
        pid = self._start_detached_redirected(cmd, FUNNEL_LOG_FILE)
        self._funnel_pid = pid
        self._set_running(pid is not None)
        if pid is not None:
            self._tail_timer.start()
        else:
            logger.warning("Failed to start the Funnel process.")
            self.error_occurred.emit("Failed to start the Funnel process.")

    def _cleanup_sync(self, settings: Dict) -> None:
        self._run_blocking(self._wrap_sudo(settings, ["pkill", "tailscaled"]))
        self._remove_socket(settings)

    def _remove_socket(self, settings: Dict) -> None:
        if IS_WINDOWS:
            return
        self._run_blocking(self._wrap_sudo(settings, ["rm", "-f", settings["socket_path"]]))

    def _wrap_sudo(self, settings: Dict, args: List[str]) -> Tuple[str, List[str]]:
        if settings.get("use_sudo") and not IS_WINDOWS:
            return "sudo", args
        return args[0], args[1:]

    def _run_blocking(self, cmd_args: Tuple[str, List[str]]) -> None:
        """Run a short cleanup command synchronously and swallow failures."""
        cmd, args = cmd_args
        proc = QProcess()
        proc.start(cmd, args)
        proc.waitForFinished(5000)

    @staticmethod
    def _sudo_is_passwordless() -> bool:
        """Check `sudo -n true` so we fail fast instead of hanging silently.

        The daemon/funnel processes run detached with no TTY, so if sudo
        needs to prompt for a password it will just hang or fail silently
        in the background - better to catch that up front.
        """
        proc = QProcess()
        proc.start("sudo", ["-n", "true"])
        proc.waitForFinished(3000)
        return proc.exitCode() == 0

    def _start_detached_redirected(
        self, cmd_args: Tuple[str, List[str]], log_file: Path
    ) -> Optional[int]:
        """Start a process detached from this app, redirecting its output to a file."""
        cmd, args = cmd_args
        full_cmd = [cmd] + args
        redirect = f">> {shlex.quote(str(log_file))} 2>&1"
        if IS_WINDOWS:
            shell_cmd = " ".join(full_cmd) + f" {redirect}"
            ok, pid = QProcess.startDetached("cmd", ["/c", shell_cmd])
        else:
            shell_cmd = " ".join(shlex.quote(part) for part in full_cmd) + f" {redirect}"
            ok, pid = QProcess.startDetached("bash", ["-c", shell_cmd])
        return pid if ok else None

    def _poll_logs(self) -> None:
        self._daemon_offset = self._tail_file(DAEMON_LOG_FILE, self._daemon_offset, watch_url=False)
        self._funnel_offset = self._tail_file(FUNNEL_LOG_FILE, self._funnel_offset, watch_url=True)

        if self._funnel_pid is not None and not _is_pid_alive(self._funnel_pid):
            self._funnel_pid = None
            self._tail_timer.stop()
            self._set_running(False)
            self.log_line.emit("Funnel process has stopped.")

    def _tail_file(self, path: Path, offset: int, watch_url: bool) -> int:
        if not path.exists():
            return offset
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(offset)
                new_data = f.read()
                new_offset = f.tell()
        except OSError:
            return offset
        for line in new_data.splitlines():
            if not line.strip():
                continue
            self.log_line.emit(line)
            if watch_url:
                match = URL_PATTERN.search(line)
                if match:
                    self.public_url_found.emit(match.group(0))
        return new_offset

    @staticmethod
    def _file_size(path: Path) -> int:
        try:
            return path.stat().st_size
        except OSError:
            return 0

    def _set_running(self, running: bool) -> None:
        self._running = running
        self.status_changed.emit(running)

    # ------------------------------------------------------------------ #
    # Internal helpers - install/update tooling
    # ------------------------------------------------------------------ #

    def _emit_tool_output(self) -> None:
        if self._tool_process is None:
            return
        data = bytes(self._tool_process.readAllStandardOutput()).decode(
            "utf-8", errors="replace"
        )
        for line in data.splitlines():
            if line.strip():
                self.tool_log.emit(line)

    def _on_tool_finished(self, *_args) -> None:
        self._tool_process = None
        self.tool_busy_changed.emit(False)
        self.tool_log.emit("Done.")

    # ------------------------------------------------------------------ #
    # Internal helpers - binary path resolution
    # ------------------------------------------------------------------ #

    def _resolve_paths(self, settings: Dict) -> None:
        if settings.get("path_mode") == "manual":
            self._tailscale_bin = self._validate_manual(settings.get("tailscale_path", ""))
            self._tailscaled_bin = self._validate_manual(settings.get("tailscaled_path", ""))
        else:
            self._tailscale_bin = self._resolve_binary("tailscale")
            self._tailscaled_bin = self._resolve_binary("tailscaled")

    @staticmethod
    def _validate_manual(path: str) -> Optional[str]:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path
        return None

    @staticmethod
    def _resolve_binary(name: str) -> Optional[str]:
        """Find a binary's full path, checking PATH plus common sbin dirs."""
        found = shutil.which(name)
        if found:
            return found
        for directory in EXTRA_BINARY_DIRS:
            candidate = os.path.join(directory, name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return None
