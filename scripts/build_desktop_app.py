"""One-Click Desktop Packaging Script for EcoStream (.app / .dmg on macOS, .exe on Windows).

Build in a clean virtualenv so only EcoStream's dependencies are bundled:
    python -m venv .venv-build
    .venv-build/bin/pip install -r requirements-desktop.txt
    .venv-build/bin/python scripts/build_desktop_app.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"


def build() -> None:
    os.environ.setdefault("PYINSTALLER_CONFIG_DIR", str(BUILD_DIR / "pyinstaller_cache"))
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sep = ";" if sys.platform == "win32" else ":"

    # Remove stale spec file to prevent cross-platform path pollution
    spec_file = ROOT / "EcoStream.spec"
    if spec_file.exists():
        try:
            spec_file.unlink()
        except OSError:
            pass

    data_args = [
        f"--add-data=ecostream/app/static{sep}ecostream/app/static",
        f"--add-data=data/samples{sep}data/samples",
        f"--add-data=data/test_documents{sep}data/test_documents",
    ]

    hidden_imports = [
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=ecostream.app.server",
        "--hidden-import=multipart",
        "--hidden-import=python_multipart",
        "--hidden-import=cryptography",
        "--hidden-import=webview",
        "--collect-submodules=webview",
        "--collect-data=webview",
        "--collect-data=magika",
        "--copy-metadata=magika",
    ]

    # EcoStream never uses these. They get pulled in only when building inside a
    # shared environment (e.g. conda base) and would bloat the app to several GB.
    excluded = [
        "torch", "torchvision", "tensorflow", "tensorboard", "keras", "jax", "jaxlib",
        "easyocr", "cv2", "pytesseract", "pdf2image", "transformers", "sklearn",
        "scipy", "matplotlib", "IPython", "notebook", "pandas.tests", "nvidia",
    ]
    exclude_args = [f"--exclude-module={m}" for m in excluded]

    icon_path = ROOT / "scripts" / "ecostream.ico"
    icon_args = [f"--icon={icon_path}"] if icon_path.exists() else []

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name=EcoStream",
        *icon_args,
        *data_args,
        *hidden_imports,
        *exclude_args,
        str(ROOT / "scripts" / "desktop_launcher.py"),
    ]

    print("[1/2] Building standalone desktop application with PyInstaller...")
    subprocess.run(cmd, cwd=str(ROOT), check=True)

    if sys.platform == "darwin":
        app_path = DIST_DIR / "EcoStream.app"
        dmg_staging = DIST_DIR / "dmg_staging"
        dmg_path = DIST_DIR / "EcoStream-Installer.dmg"

        if app_path.exists():
            print(f"[✓] Built macOS App Bundle: {app_path}")
            # Always produce guaranteed ZIP archive
            zip_out = shutil.make_archive(str(DIST_DIR / "EcoStream-macOS-App"), "zip", root_dir=str(DIST_DIR), base_dir="EcoStream.app")
            print(f"[✓] Created macOS App Archive: {zip_out}")

            print("[2/2] Packaging macOS Disk Image (EcoStream-Installer.dmg)...")
            try:
                if dmg_staging.exists():
                    shutil.rmtree(dmg_staging)
                dmg_staging.mkdir(parents=True, exist_ok=True)
                shutil.copytree(app_path, dmg_staging / "EcoStream.app", symlinks=True)
                try:
                    os.symlink("/Applications", dmg_staging / "Applications")
                except Exception:
                    pass

                if dmg_path.exists():
                    dmg_path.unlink()

                subprocess.run(
                    [
                        "hdiutil",
                        "create",
                        "-volname",
                        "EcoStream AI Carbon Installer",
                        "-srcfolder",
                        str(dmg_staging),
                        "-ov",
                        "-format",
                        "UDZO",
                        str(dmg_path),
                    ],
                    check=True,
                )
                print(f"[✓] Successfully created macOS Installer DMG: {dmg_path}")
            except Exception as e:
                print(f"[!] Note: hdiutil DMG creation skipped or requires elevated device access ({e}).")
            finally:
                shutil.rmtree(dmg_staging, ignore_errors=True)
    elif sys.platform == "win32":
        exe_dir = DIST_DIR / "EcoStream"
        zip_path = DIST_DIR / "EcoStream-Windows-Desktop"
        if exe_dir.exists():
            print(f"[✓] Built Windows Executable Folder: {exe_dir / 'EcoStream.exe'}")
            print("[2/2] Creating distributable ZIP archive for Windows SMEs...")
            archive = shutil.make_archive(str(zip_path), "zip", root_dir=str(DIST_DIR), base_dir="EcoStream")
            print(f"[✓] Successfully created Windows Portable Installer: {archive}")


if __name__ == "__main__":
    build()
