@echo off
setlocal
cd /d "%~dp0"
title prxmpt 1.0.15 Update Builder
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_windows.ps1"
if errorlevel 1 (
  echo.
  echo prxmpt update build failed. Copy the complete error shown above.
  pause
  exit /b 1
)
echo.
echo prxmptUpdate_1.0.15.exe was created successfully.
pause
