"""Standalone Cross-Platform Desktop Launcher for EcoStream (.app / .dmg / .exe).

Starts the local FastAPI server strictly on 127.0.0.1 (Zero-Cloud-Leak Local-Only mode)
and opens EcoStream in a dedicated desktop application window.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import webbrowser
import uvicorn

from ecostream.app.server import app, find_available_port


def _open_native_app_window(url: str) -> None:
    """Open URL in a chromeless desktop app window if Chrome/Edge/Brave is installed, else default browser."""
    time.sleep(1.2)
    try:
        if sys.platform == "darwin":
            mac_browsers = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            ]
            for bin_path in mac_browsers:
                if os.path.exists(bin_path):
                    subprocess.Popen([bin_path, f"--app={url}", "--new-window"])
                    return
        elif sys.platform == "win32":
            win_browsers = [
                os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            ]
            for bin_path in win_browsers:
                if os.path.exists(bin_path):
                    subprocess.Popen([bin_path, f"--app={url}", "--new-window"])
                    return
    except Exception:
        pass

    webbrowser.open(url)


def main() -> None:
    # Strictly bind to 127.0.0.1 for local-only SME data security
    host = "127.0.0.1"
    port = find_available_port(8000, host)
    url = f"http://{host}:{port}"

    # When frozen as a GUI app (.app / .exe without console), redirect stdout/stderr to a log file
    # because uvicorn's default logging formatter checks sys.stdout.isatty()
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

    threading.Thread(target=_open_native_app_window, args=(url,), daemon=True).start()

    print("============================================================")
    print("  EcoStream AI Carbon Accounting — SME Desktop Edition")
    print(f"  Local Security Binding : {url} (100% Offline / Local-Only)")
    print(f"  Live Workflow Monitor  : {url}/monitor")
    print("============================================================")

    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
