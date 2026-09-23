@echo off
setlocal

set PYTHON_VERSION=3.12.8
set ARCH=amd64
set RUNTIME_DIR=runtime
set TARGET_DIR=%RUNTIME_DIR%\python-%PYTHON_VERSION%
set ZIP_FILENAME=python-%PYTHON_VERSION%-embed-%ARCH%.zip
set DOWNLOAD_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%ZIP_FILENAME%

for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do set PTH_FILENAME=python%%a%%b._pth

cd /d "%~dp0"

echo Python version: %PYTHON_VERSION%
echo Target directory: %TARGET_DIR%
echo.

if not exist "%RUNTIME_DIR%\" mkdir "%RUNTIME_DIR%"

if exist "%TARGET_DIR%\python.exe" (
    echo Embedded Python already exists. Reusing it.
) else (
    echo Downloading Embedded Python from %DOWNLOAD_URL% ...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%ZIP_FILENAME%'"
    if errorlevel 1 goto :error

    mkdir "%TARGET_DIR%"
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%ZIP_FILENAME%' -DestinationPath '%TARGET_DIR%'"
    if errorlevel 1 goto :error

    del "%ZIP_FILENAME%" >nul 2>&1

    set PTH_FILEPATH=%TARGET_DIR%\%PTH_FILENAME%
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$path = '%TARGET_DIR%\%PTH_FILENAME%'; $content = (Get-Content -Path $path -Raw) -replace '#import site', 'import site'; $encoding = New-Object System.Text.UTF8Encoding($false); [System.IO.File]::WriteAllText($path, $content, $encoding)"
    if errorlevel 1 goto :error
)

call "%~dp0setenv.bat"
if errorlevel 1 goto :error

if not exist "%APP_LOCAL_DIR%\" mkdir "%APP_LOCAL_DIR%"

"%PYTHON_EXECUTABLE%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo Installing pip...
    set GET_PIP_PATH=%TARGET_DIR%\get-pip.py
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%TARGET_DIR%\get-pip.py'"
    if errorlevel 1 goto :error
    "%PYTHON_EXECUTABLE%" "%TARGET_DIR%\get-pip.py"
    if errorlevel 1 goto :error
)

echo Installing project and development dependencies...
"%PYTHON_EXECUTABLE%" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo.
echo Verifying bootstrap...
"%PYTHON_EXECUTABLE%" --version
"%PYTHON_EXECUTABLE%" -m tradingview_screening --help >nul
if errorlevel 1 goto :error

echo.
echo Setup complete.
pause
exit /b 0

:error
echo.
echo Setup failed. Exit code: %errorlevel%
pause
exit /b 1
