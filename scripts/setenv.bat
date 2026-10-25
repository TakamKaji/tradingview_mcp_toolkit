@echo off

for %%I in ("%~dp0..") do set "DP0=%%~fI"

set "PYTHON_VERSION=3.12.8"
set "PYTHON_PATH=%DP0%\runtime\python-%PYTHON_VERSION%"
set "APP_LOCAL_DIR=%DP0%\.local"

rem Keep the Windows user environment intact.
rem Only isolate Python selection from any system Python configuration.
set "PYTHONHOME="
set "PYTHONPATH="

set "PYTHON_EXECUTABLE=%PYTHON_PATH%\python.exe"
set "PYTHONW_EXECUTABLE=%PYTHON_PATH%\pythonw.exe"
set "PYTHON_BIN_PATH=%PYTHON_EXECUTABLE%"
set "PYTHON_LIB_PATH=%PYTHON_PATH%\Lib\site-packages"
set "PATH=%PYTHON_PATH%;%PYTHON_PATH%\Scripts;%PATH%"
