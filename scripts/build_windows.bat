REM Copyright (c) 2026 Draconov
REM SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

@echo off
setlocal
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1"
if errorlevel 1 exit /b %errorlevel%
endlocal
