"""
Command-line interface for Funnel-Forge.

Running the app (or the built binary) with no arguments opens the GUI,
same as always. Passing a subcommand instead runs headlessly - useful
for scripting, cron/systemd, or a terminal-only environment.

Examples:
    funnel-forge start --hostname boffin-io --port 3000
    funnel-forge stop
    funnel-forge status
    funnel-forge version
    funnel-forge install-tailscale
    funnel-forge update-tailscale
"""

import argparse
import sys
from typing import Optional

from PyQt6.QtCore import QCoreApplication

from core.funnel_controller import FunnelController
from core.logger import get_logger
from core.settings import IS_WINDOWS, load_settings, save_settings

APP_VERSION = "0.1.0"

logger = get_logger("cli")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="funnel-forge",
        description="Tailscale Funnel Manager. With no arguments, opens the GUI.",
    )
    parser.add_argument(
        "--app-version", action="version", version=f"Funnel-Forge {APP_VERSION}"
    )
    subparsers = parser.add_subparsers(dest="command")

    start_p = subparsers.add_parser("start", help="Start the Tailscale Funnel")
    start_p.add_argument("--hostname", help="Tailscale hostname (overrides saved setting)")
    start_p.add_argument("--port", type=int, help="Local port to expose (overrides saved setting)")
    start_p.add_argument("--socket-path", help="tailscaled socket path (overrides saved setting)")
    sudo_group = start_p.add_mutually_exclusive_group()
    sudo_group.add_argument(
        "--sudo", dest="use_sudo", action="store_true", default=None, help="Use sudo"
    )
    sudo_group.add_argument(
        "--no-sudo", dest="use_sudo", action="store_false", help="Don't use sudo"
    )

    subparsers.add_parser("stop", help="Stop the Tailscale Funnel")
    subparsers.add_parser("status", help="Show whether the Funnel is currently running")
    subparsers.add_parser("version", help="Show the installed Tailscale version")
    subparsers.add_parser(
        "install-tailscale", help="Install Tailscale (runs the official install script)"
    )
    subparsers.add_parser("update-tailscale", help="Update Tailscale to the latest version")

    return parser


def _attach_windows_console() -> None:
    """On Windows, a --windowed-built binary has no console by default.

    Attach to the parent console (the terminal the user ran it from) so
    CLI output is actually visible there instead of vanishing silently.
    """
    if not IS_WINDOWS:
        return
    try:
        import ctypes

        ATTACH_PARENT_PROCESS = -1
        if ctypes.windll.kernel32.AttachConsole(ATTACH_PARENT_PROCESS):
            sys.stdout = open("CONOUT$", "w")  # noqa: SIM115
            sys.stderr = open("CONOUT$", "w")  # noqa: SIM115
    except Exception:
        pass  # best-effort only; GUI mode never reaches here anyway


def run_cli(args: argparse.Namespace) -> int:
    _attach_windows_console()
    logger.info("Running CLI command: %s", args.command)

    app = QCoreApplication(sys.argv)
    settings = load_settings()
    controller = FunnelController()
    controller.log_line.connect(print)

    exit_code = {"value": 0}

    if args.command == "start":
        if args.hostname:
            settings["hostname"] = args.hostname
        if args.port:
            settings["port"] = args.port
        if args.socket_path:
            settings["socket_path"] = args.socket_path
        if args.use_sudo is not None:
            settings["use_sudo"] = args.use_sudo
        save_settings(settings)

        finished = {"value": False}

        def on_status(running: bool) -> None:
            finished["value"] = True
            if running:
                print("Funnel is running.")
            app.quit()

        def on_error(message: str) -> None:
            finished["value"] = True
            print(f"Error: {message}", file=sys.stderr)
            exit_code["value"] = 1
            app.quit()

        def on_url(url: str) -> None:
            print(f"Public URL: {url}")

        def on_auth(url: str) -> None:
            print("Tailscale authentication needed. Open this URL in a browser:")
            print(url)

        controller.status_changed.connect(on_status)
        controller.error_occurred.connect(on_error)
        controller.public_url_found.connect(on_url)
        controller.auth_required.connect(on_auth)

        controller.start(settings)
        # Qt's app.quit() has no effect before an event loop is running, so
        # if start() already finished (or failed) synchronously above, skip
        # exec() entirely instead of hanging forever waiting for a quit
        # request that was already sent and lost.
        if not finished["value"]:
            app.exec()
        return exit_code["value"]

    if args.command == "stop":
        controller.stop(settings)
        print("Stopped.")
        return 0

    if args.command == "status":
        controller.detect_existing_session()
        print("Funnel is running." if controller.is_running() else "Funnel is stopped.")
        return 0

    if args.command == "version":
        result: dict = {}

        def on_version(text: str) -> None:
            result["text"] = text

        controller.version_result.connect(on_version)
        controller.check_version(settings)
        print(f"Tailscale: {result.get('text', 'unknown')}")
        return 0

    if args.command in ("install-tailscale", "update-tailscale"):
        controller.tool_log.connect(print)
        finished = {"value": False}

        def on_busy(busy: bool) -> None:
            if not busy:
                finished["value"] = True
                app.quit()

        controller.tool_busy_changed.connect(on_busy)
        if args.command == "install-tailscale":
            controller.install_tailscale()
        else:
            controller.update_tailscale(settings)
        if not finished["value"]:
            app.exec()
        return exit_code["value"]

    return 0


def maybe_run_cli(argv: Optional[list] = None) -> Optional[int]:
    """Parse argv; return an exit code if a CLI subcommand ran, else None (open the GUI)."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        return None
    return run_cli(args)
