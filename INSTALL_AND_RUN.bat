@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python 3.12 or 3.13 is required.
  echo Install it from https://www.python.org/downloads/windows/
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating the ClearCue environment...
  py -3.12 -m venv .venv 2>nul
  if errorlevel 1 py -3.13 -m venv .venv
  if not exist ".venv\Scripts\python.exe" (
    echo ClearCue could not create a Python 3.12 or 3.13 environment.
    pause
    exit /b 1
  )
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto :failed
python -m pip install -e .
if errorlevel 1 goto :failed
python -m clearcue
exit /b 0

:failed
echo.
echo Installation failed. Check your internet connection and try again.
pause
exit /b 1
