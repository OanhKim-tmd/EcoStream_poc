"""Standalone Native Desktop Launcher for EcoStream (.app / .dmg / .exe / Tauri).

Features:
1. Native App Window Mode:
   - Uses PyWebView (Native Cocoa on macOS / WebView2 on Windows) if available.
   - Or launches Edge/Chrome in dedicated Native App Mode (--app=http://127.0.0.1:PORT)
     without browser URL bar or tabs, giving a 100% native desktop app experience.
2. Zero-Cloud-Leak Local Server:
   - Strictly binds to 127.0.0.1.
3. Clean Lifecycle Management:
   - Closes background Python server cleanly when window is closed.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
import uvicorn

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from ecostream.app.server import app, find_available_port


def _is_ecostream_running(host: str = "127.0.0.1", port: int = 8000) -> bool:
    """Check if an EcoStream server instance is already responding on host:port."""
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/api/auth/status", timeout=0.8) as resp:
            return resp.status == 200
    except Exception:
        return False


def _wait_until_ready(host: str, port: int, timeout_sec: float = 12.0) -> bool:
    """Poll the local server socket until it accepts connections."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.3):
                return True
        except OSError:
            time.sleep(0.15)
    return False


def _open_native_app_window(url: str) -> bool:
    """Launch in standalone Dedicated App Mode (no URL bar, no tabs, native window look)."""
    try:
        # Windows: Try Edge App Mode (guaranteed pre-installed on Win 10/11)
        if sys.platform == "win32":
            edge_paths = [
                os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
            ]
            for p in edge_paths:
                if os.path.exists(p):
                    subprocess.Popen([p, f"--app={url}"])
                    return True

            # Try Chrome on Windows
            chrome_paths = [
                os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            ]
            for p in chrome_paths:
                if os.path.exists(p):
                    subprocess.Popen([p, f"--app={url}"])
                    return True

            # Fallback to shell start with edge
            try:
                subprocess.Popen(f'start msedge --app="{url}"', shell=True)
                return True
            except Exception:
                pass

        # macOS: Try Chrome or Edge App Mode
        elif sys.platform == "darwin":
            mac_browsers = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            ]
            for b in mac_browsers:
                if os.path.exists(b):
                    subprocess.Popen([b, f"--app={url}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True

            # macOS Safari / default app notification
            subprocess.Popen(
                [
                    "/usr/bin/osascript",
                    "-e",
                    f'display notification "Đang mở cửa sổ ứng dụng tại {url}" with title "EcoStream AI Carbon"',
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.Popen(["/usr/bin/open", url])
            return True
    except Exception:
        pass

    # Generic fallback
    try:
        webbrowser.open(url, new=1, autoraise=True)
        return True
    except Exception:
        return False


def main() -> None:
    host = "127.0.0.1"

    # When frozen as GUI app (.app / .exe without console), redirect stdout/stderr to log file
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

    # 1. If EcoStream is already running on port 8000, bring window to front
    if _is_ecostream_running(host, 8000):
        url = f"http://{host}:8000"
        print(f"[EcoStream Desktop] Existing instance running at {url}, bringing window to front...")
        _open_native_app_window(url)
        return

    # 2. Start local server
    port = find_available_port(8000, host)
    url = f"http://{host}:{port}"

    # Try PyWebView for 100% native Cocoa/WebView2 window if installed
    use_pywebview = False
    try:
        import webview
        use_pywebview = True
    except ImportError:
        use_pywebview = False

    if use_pywebview:
        # Run Uvicorn in background daemon thread
        server_thread = threading.Thread(
            target=lambda: uvicorn.run(app, host=host, port=port, log_level="warning"),
            daemon=True,
        )
        server_thread.start()

        # Wait until port accepts connections
        _wait_until_ready(host, port, timeout_sec=12.0)

        # Open pure native desktop window
        import webview
        window = webview.create_window(
            title="EcoStream AI Carbon Accounting",
            url=url,
            width=1320,
            height=880,
            min_size=(1024, 700),
            confirm_close=False,
        )
        webview.start()
        # When window is closed, cleanly exit process
        sys.exit(0)
    else:
        # Fallback to Dedicated App Window Mode (Edge/Chrome Standalone App Window)
        def _launch_when_ready() -> None:
            _wait_until_ready(host, port, timeout_sec=12.0)
            _open_native_app_window(url)

        threading.Thread(target=_launch_when_ready, daemon=True).start()

        print("============================================================")
        print("  EcoStream AI Carbon Accounting — Standalone Desktop Mode")
        print(f"  Local Binding : {url} (Zero-Cloud-Leak / 100% Local)")
        print("============================================================")

        uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
