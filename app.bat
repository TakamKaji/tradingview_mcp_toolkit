@echo off
setlocal

cd /d "%~dp0"
call "%~dp0setenv.bat"
if errorlevel 1 exit /b %errorlevel%

if not exist "%PYTHON_EXECUTABLE%" (
    echo Embedded Python was not found. Run setup.bat first. 1>&2
    exit /b 1
)

"%PYTHON_EXECUTABLE%" -m tradingview_screening %*
exit /b %errorlevel%
