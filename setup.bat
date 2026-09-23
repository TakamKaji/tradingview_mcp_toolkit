@echo off
setlocal

REM --- 設定 ---
REM ダウンロードしたいPythonのバージョンとアーキテクチャを指定します
set PYTHON_VERSION=3.12.8
set ARCH=amd64

REM 最終的に作成されるディレクトリ名
set TARGET_DIR=python-%PYTHON_VERSION%
REM --- 設定ここまで ---

REM .pthファイル名を動的に生成 (例: python313._pth)
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do set PTH_FILENAME=python%%a%%b._pth

set ZIP_FILENAME=python-%PYTHON_VERSION%-embed-%ARCH%.zip
set DOWNLOAD_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%ZIP_FILENAME%

echo Python version: %PYTHON_VERSION%
echo Target directory: %TARGET_DIR%
echo.

REM ターゲットディレクトリが既に存在するかチェック
if exist "%TARGET_DIR%\" (
    echo [%TARGET_DIR%] directory already exists. Skipping setup.
    pause
    goto :eof
)

echo Downloading from %DOWNLOAD_URL% ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri %DOWNLOAD_URL% -OutFile %ZIP_FILENAME%"

if not exist "%ZIP_FILENAME%" (
    echo Download failed. Please check the version number and your internet connection.
    pause
    goto :eof
)
echo Download complete.
echo.

echo Creating directory and extracting files into %TARGET_DIR%...
mkdir "%TARGET_DIR%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%ZIP_FILENAME%' -DestinationPath '%TARGET_DIR%'"
echo Extraction complete.
echo.

echo Enabling site-packages by uncommenting 'import site' in %PTH_FILENAME%...
set PTH_FILEPATH=%TARGET_DIR%\%PTH_FILENAME%
powershell -NoProfile -ExecutionPolicy Bypass -Command "$path = '%PTH_FILEPATH%'; $content = (Get-Content -Path $path -Raw) -replace '#import site', 'import site'; $encoding = New-Object System.Text.UTF8Encoding($false); [System.IO.File]::WriteAllText($path, $content, $encoding)"
echo Done.
echo.

echo Downloading get-pip.py...
set GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py
set GET_PIP_PATH=%TARGET_DIR%\get-pip.py
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri %GET_PIP_URL% -OutFile %GET_PIP_PATH%"
echo Download complete.
echo.

echo Running environment setup script...
call setenv.bat

echo Creating local environment directories...
if not exist "%LOCALENV_DIR%\_tmp" mkdir "%LOCALENV_DIR%\_tmp"
if not exist "%LOCALENV_DIR%\userprofile" mkdir "%LOCALENV_DIR%\userprofile"
if not exist "%LOCALENV_DIR%\localappdata" mkdir "%LOCALENV_DIR%\localappdata"
if not exist "%LOCALENV_DIR%\userroaming" mkdir "%LOCALENV_DIR%\userroaming"
echo Done.
echo.

echo Installing pip...
%TARGET_DIR%\python.exe %GET_PIP_PATH%
echo Installation complete.
echo.

echo Cleaning up...
del "%ZIP_FILENAME%"
@REM del "%GET_PIP_PATH%"
echo.


echo Verifying installation...
%TARGET_DIR%\python.exe --version
@REM %TARGET_DIR%\Scripts\pip.exe --version
echo.

echo Installing required packages from requirements.txt...
%TARGET_DIR%\python.exe -m pip install -r requirements.txt
echo Package installation complete.
echo.

echo Installing Playwright Chromium browser...
%TARGET_DIR%\python.exe -m playwright install chromium
echo Browser installation complete.
echo.

echo Setup complete. Python is ready in the '%TARGET_DIR%' directory.

pause

endlocal