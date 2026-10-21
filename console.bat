@echo off
setlocal
title TradingView MCP Support Console

call "%~dp0setenv.bat"
cd /d "%~dp0"

if not exist "%PYTHON_EXECUTABLE%" (
    echo Embedded Python was not found.
    echo Run setup.bat first.
    pause
    exit /b 1
)

echo ========================================================
echo  TradingView MCP Support - Portable Python Console
echo ========================================================
echo.
echo  Common commands:
echo    python -m tradingview_screening --help
echo    python -m pip install --no-build-isolation -r requirements-dev.txt ^(first time for development^)
echo    python -m pytest
echo    python -m ruff check .
echo.

cmd /k
