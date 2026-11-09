@echo off
rem Builds both portable versions of RedactR (no installation and no Python needed on target PCs):
rem   dist\RedactR.exe        - one self-contained file (slower start: unpacks itself each launch)
rem   dist\RedactR-Fast\      - folder version, starts in a couple of seconds (+ RedactR-Fast.zip to share)
rem If Tesseract OCR is installed on this machine, a trimmed copy is bundled into both.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    where py >nul 2>nul && (py -3 -m venv .venv) || (python -m venv .venv)
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
".venv\Scripts\python.exe" -m pip install pyinstaller pefile
".venv\Scripts\python.exe" packaging\make_icon.py
".venv\Scripts\python.exe" packaging\make_splash.py
copy /Y packaging\redactr.ico redactr\assets\redactr.ico >nul
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    ".venv\Scripts\python.exe" packaging\prepare_tesseract.py
) else (
    echo Tesseract OCR not installed - building without OCR. To include it: winget install UB-Mannheim.TesseractOCR
)

echo Building single-file RedactR.exe ...
set REDACTR_BUILD=
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --distpath dist --workpath build packaging\RedactR.spec
if errorlevel 1 goto failed

echo Building fast-start folder RedactR-Fast ...
set REDACTR_BUILD=folder
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --distpath dist --workpath build_folder packaging\RedactR.spec
if errorlevel 1 goto failed
set REDACTR_BUILD=
powershell -NoProfile -Command "Compress-Archive -Path 'dist\RedactR-Fast' -DestinationPath 'dist\RedactR-Fast.zip' -Force"

echo.
echo Done:
echo   dist\RedactR.exe       single file - copy anywhere and double-click
echo   dist\RedactR-Fast.zip  fast-start version - unzip, then run RedactR-Fast\RedactR.exe
pause
exit /b 0

:failed
echo Build failed.
pause
exit /b 1
