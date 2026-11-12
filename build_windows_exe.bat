@echo off
echo ============================================================
echo   EcoStream AI Carbon Accounting - Windows .EXE Builder
echo ============================================================
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -r requirements.txt pyinstaller cryptography
python scripts\build_desktop_app.py
echo.
echo [DONE] File .exe nam tai: dist\EcoStream\EcoStream.exe
echo        File nen phan phoi: dist\EcoStream-Windows-Desktop.zip
pause

