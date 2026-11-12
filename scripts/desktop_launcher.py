"""Standalone Cross-Platform Desktop Launcher for EcoStream (.app / .dmg / .exe).

Starts the local FastAPI server strictly on 127.0.0.1 (Zero-Cloud-Leak Local-Only mode)
and opens EcoStream immediately in the user's active browser with native OS feedback.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
import uvicorn

from ecostream.app.server import app, find_available_port


def _is_ecostream_running(host: str = "127.0.0.1", port: int = 8000) -> bool:
    """Check if an EcoStream server instance is already responding on host:port."""
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/api/auth/status", timeout=0.8) as resp:
            return resp.status == 200
    except Exception:
        return False


def _wait_until_ready(host: str, port: int, timeout_sec: float = 10.0) -> bool:
    """Poll the local server socket until it accepts connections."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.3):
                return True
        except OSError:
            time.sleep(0.15)
    return False


def _open_url_foreground(url: str) -> None:
    """Reliably open URL and bring window to foreground on macOS, Windows, and Linux."""
    try:
        if sys.platform == "darwin":
            # Show native macOS notification for instant visual feedback
            subprocess.Popen(
                [
                    "/usr/bin/osascript",
                    "-e",
                    f'display notification "Đang mở giao diện tại {url}" with title "EcoStream AI Carbon"',
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.Popen(["/usr/bin/open", url])
            return
        elif sys.platform == "win32":
            os.startfile(url)  # type: ignore[attr-defined]
            return
    except Exception:
        pass

    webbrowser.open(url, new=1, autoraise=True)


def main() -> None:
    host = "127.0.0.1"

    # When frozen as a GUI app (.app / .exe without console), redirect stdout/stderr to a log file
    if getattr(sys, "frozen", False) and (sys.stdout is None or sys.stderr is None):
        if sys.platform == "darwin":
            log_dir = os.path.expanduser("~/Library/Logs/EcoStream")
        elif sys.platform == "win32":
            log_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "EcoStream", "logs")
        else:
            log_dir = os.path.expanduser("~/.ecostream/logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = open(os.path.join(log_dir, "ecostream_desktop.log"), "a", encoding="utf-8")
        sys.stdout = log_file
        sys.stderr = log_file

    # 1. If EcoStream is already running on port 8000, just bring it to the foreground immediately!
    if _is_ecostream_running(host, 8000):
        url = f"http://{host}:8000"
        print(f"[EcoStream Desktop] Existing instance detected at {url}, opening window...")
        _open_url_foreground(url)
        return

    # 2. Otherwise start a new local server instance and open window as soon as ready
    port = find_available_port(8000, host)
    url = f"http://{host}:{port}"

    def _launch_when_ready() -> None:
        _wait_until_ready(host, port, timeout_sec=12.0)
        _open_url_foreground(url)

    threading.Thread(target=_launch_when_ready, daemon=True).start()

    print("============================================================")
    print("  EcoStream AI Carbon Accounting — SME Desktop Edition")
    print(f"  Local Security Binding : {url} (100% Offline / Local-Only)")
    print(f"  Live Workflow Monitor  : {url}/monitor")
    print("============================================================")

    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
