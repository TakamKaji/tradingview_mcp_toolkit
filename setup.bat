@echo off
setlocal EnableExtensions
rem ASCII-only launcher. Japanese user messages live in scripts/setup-ui.ps1.
cd /d "%~dp0"
if errorlevel 1 exit /b 1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup-ui.ps1" %*
set "SETUP_EXIT=%errorlevel%"
exit /b %SETUP_EXIT%
