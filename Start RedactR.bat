@echo off
rem RedactR launcher - sets up a private Python environment on first run, then starts the app.
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo First run: setting up RedactR ^(one time, needs Python 3.10+^)...
    where py >nul 2>nul && (py -3 -m venv .venv) || (python -m venv .venv)
    if not exist ".venv\Scripts\python.exe" (
        echo Python was not found. Install it from https://www.python.org/downloads/ and run this again.
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
start "" ".venv\Scripts\pythonw.exe" "RedactR.pyw"
