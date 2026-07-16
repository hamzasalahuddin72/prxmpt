@echo off
setlocal
cd /d "%~dp0"
title ClearCue 1.0.7 Update Builder
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_windows.ps1"
if errorlevel 1 (
  echo.
  echo ClearCue installer build failed. Copy the complete error shown above.
  pause
  exit /b 1
)
echo.
echo ClearCueUpdate_1.0.7.exe was created successfully.
pause
