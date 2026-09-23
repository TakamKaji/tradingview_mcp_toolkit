@echo off

set "DP0=%~dp0"
set "DP0=%DP0:~0,-1%"

set "PYTHON_VERSION=3.12.8"
set "PYTHON_PATH=%DP0%\runtime\python-%PYTHON_VERSION%"
set "LOCALENV_DIR=%DP0%\.local\env"

set "TMP=%LOCALENV_DIR%\_tmp"
set "TEMP=%LOCALENV_DIR%\_tmp"
set "HOME=%LOCALENV_DIR%\userprofile"
set "HOMEPATH=%LOCALENV_DIR%\userprofile"
set "USERPROFILE=%LOCALENV_DIR%\userprofile"
set "LOCALAPPDATA=%LOCALENV_DIR%\localappdata"
set "APPDATA=%LOCALENV_DIR%\userroaming"

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONEXECUTABLE=%PYTHON_PATH%\python.exe"
set "PYTHONWEXECUTABLE=%PYTHON_PATH%\pythonw.exe"

set "PYTHON_EXECUTABLE=%PYTHON_PATH%\python.exe"
set "PYTHONW_EXECUTABLE=%PYTHON_PATH%\pythonw.exe"
set "PYTHON_BIN_PATH=%PYTHON_EXECUTABLE%"
set "PYTHON_LIB_PATH=%PYTHON_PATH%\Lib\site-packages"
set "PATH=%PYTHON_PATH%;%PYTHON_PATH%\Scripts;%PATH%"
