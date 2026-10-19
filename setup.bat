@echo off
setlocal EnableExtensions

set "PYTHON_VERSION=3.12.8"
set "ARCH=amd64"
set "RUNTIME_DIR=runtime"
set "TARGET_DIR=%RUNTIME_DIR%\python-%PYTHON_VERSION%"
set "ZIP_FILENAME=python-%PYTHON_VERSION%-embed-%ARCH%.zip"
set "DOWNLOAD_PATH=%RUNTIME_DIR%\%ZIP_FILENAME%"
set "DOWNLOAD_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%ZIP_FILENAME%"
set "NO_PAUSE="

if /I "%~1"=="--no-pause" set "NO_PAUSE=1"

for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set "PTH_FILENAME=python%%a%%b._pth"
    set "STDLIB_FILENAME=python%%a%%b.zip"
    set "DLL_FILENAME=python%%a%%b.dll"
)

cd /d "%~dp0"
if errorlevel 1 goto :error

echo Python version: %PYTHON_VERSION%
echo Target directory: %TARGET_DIR%
echo.

if not exist "%RUNTIME_DIR%\" mkdir "%RUNTIME_DIR%"
if errorlevel 1 goto :error

set "RUNTIME_HEALTHY="
if exist "%TARGET_DIR%\python.exe" if exist "%TARGET_DIR%\%PTH_FILENAME%" if exist "%TARGET_DIR%\%STDLIB_FILENAME%" if exist "%TARGET_DIR%\%DLL_FILENAME%" (
    "%TARGET_DIR%\python.exe" -I -c "import sys, encodings, ssl, pathlib; assert '.'.join(map(str, sys.version_info[:3])) == '%PYTHON_VERSION%'; assert any(line.strip() in ('#import site', 'import site') for line in pathlib.Path(sys.executable).with_name('%PTH_FILENAME%').read_text().splitlines())" >nul 2>&1
    if not errorlevel 1 set "RUNTIME_HEALTHY=1"
)

if defined RUNTIME_HEALTHY (
    echo Embedded Python already exists. Reusing it.
) else (
    if exist "%TARGET_DIR%\" (
        echo Incomplete Embedded Python runtime found. Rebuilding it.
        rmdir /s /q "%TARGET_DIR%"
        if exist "%TARGET_DIR%\" goto :error
    )

    if exist "%DOWNLOAD_PATH%" del /q "%DOWNLOAD_PATH%" >nul 2>&1

    echo Downloading Embedded Python from %DOWNLOAD_URL% ...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri $env:DOWNLOAD_URL -OutFile $env:DOWNLOAD_PATH"
    if errorlevel 1 goto :error

    mkdir "%TARGET_DIR%"
    if errorlevel 1 goto :error

    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "Expand-Archive -LiteralPath $env:DOWNLOAD_PATH -DestinationPath $env:TARGET_DIR"
    if errorlevel 1 goto :error

    del /q "%DOWNLOAD_PATH%" >nul 2>&1

)

set "PTH_FILEPATH=%TARGET_DIR%\%PTH_FILENAME%"
if not exist "%PTH_FILEPATH%" (
    echo Embedded Python path configuration was not found: %PTH_FILEPATH%
    goto :error
)

rem Always enable site on rerun as well. A previous setup may have stopped after extraction.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$path = $env:PTH_FILEPATH; $content = (Get-Content -LiteralPath $path -Raw) -replace '(?m)^#import site[ \t]*(\r?)$', 'import site$1'; if ($content -notmatch '(?m)^import site[ \t]*\r?$') { throw 'Embedded Python site configuration is invalid' }; $encoding = New-Object System.Text.UTF8Encoding($false); [System.IO.File]::WriteAllText($path, $content, $encoding)"
if errorlevel 1 goto :error

call "%~dp0setenv.bat"
if errorlevel 1 goto :error

if not exist "%APP_LOCAL_DIR%\" mkdir "%APP_LOCAL_DIR%"
if errorlevel 1 goto :error

"%PYTHON_EXECUTABLE%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo Installing pip...
    if exist "%TARGET_DIR%\get-pip.py" del /q "%TARGET_DIR%\get-pip.py" >nul 2>&1
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%TARGET_DIR%\get-pip.py'"
    if errorlevel 1 goto :error

    "%PYTHON_EXECUTABLE%" "%TARGET_DIR%\get-pip.py"
    if errorlevel 1 goto :error

    del /q "%TARGET_DIR%\get-pip.py" >nul 2>&1
)

echo Installing local build backend...
"%PYTHON_EXECUTABLE%" -m pip install "setuptools>=75,<81"
if errorlevel 1 goto :error

echo Installing project runtime dependencies...
rem Embeddable Python uses pythonXY._pth isolated mode.
rem pip build isolation relies on temporary paths that this runtime does not inherit reliably,
rem so build requirements are installed above and the local project is built without isolation.
"%PYTHON_EXECUTABLE%" -m pip install --no-build-isolation -r requirements.txt
if errorlevel 1 goto :error

echo.
echo Verifying shared app entrypoint...
call "%~dp0app.bat" --help >nul
if errorlevel 1 goto :error

echo.
echo Setup complete.
echo.
echo Next steps:
echo   app.bat mcp status
echo   app.bat mcp auth
echo   app.bat mcp status
echo.
echo On a fresh machine, the first status command normally returns AUTH_REQUIRED
echo with exit code 3 until mcp auth is completed.
call :pause_if_needed
exit /b 0

:error
set "SETUP_EXIT_CODE=%errorlevel%"
if "%SETUP_EXIT_CODE%"=="0" set "SETUP_EXIT_CODE=1"
echo.
echo Setup failed. Exit code: %SETUP_EXIT_CODE%
call :pause_if_needed
exit /b %SETUP_EXIT_CODE%

:pause_if_needed
if not defined NO_PAUSE pause
exit /b 0
