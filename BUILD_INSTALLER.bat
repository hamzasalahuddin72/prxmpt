@echo off
setlocal
cd /d "%~dp0"
title prxmpt 1.0.24 UI Baseline Builder
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_windows.ps1"
if errorlevel 1 (
  echo.
  echo prxmpt installer build failed. Copy the complete error shown above.
  pause
  exit /b 1
)
echo.
echo prxmptUpdate_1.0.24.exe was created successfully.
pause
