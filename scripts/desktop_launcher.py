"""Standalone Windows Desktop Launcher for EcoStream.

Starts the local FastAPI server on an available port and automatically opens
the default web browser to the EcoStream Dashboard.
"""

import threading
import time
import webbrowser
import uvicorn
from ecostream.app.server import app, find_available_port


def main():
    host = "127.0.0.1"
    port = find_available_port(8000, host)
    url = f"http://{host}:{port}"

    def open_browser():
        time.sleep(1.5)
        print(f"[EcoStream Desktop] Opening browser at {url} ...")
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()
    print(f"============================================================")
    print(f"  EcoStream AI Carbon Accounting - Desktop Edition")
    print(f"  Dashboard URL : {url}")
    print(f"  Live Monitor  : {url}/monitor")
    print(f"  (Keep this window open while using the application)")
    print(f"============================================================")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()

