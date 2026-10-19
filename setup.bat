@echo off
setlocal EnableExtensions
rem GitHub stores this BAT as UTF-8 without BOM. Set Windows console to UTF-8 for Japanese messages.
chcp 65001 >nul

set "SETUP_STEP=初期準備"
set "SETUP_EXIT_CODE="
set "PYTHON_VERSION=3.12.8"
set "ARCH=amd64"
set "RUNTIME_DIR=runtime"
set "TARGET_DIR=%RUNTIME_DIR%\python-%PYTHON_VERSION%"
set "ZIP_FILENAME=python-%PYTHON_VERSION%-embed-%ARCH%.zip"
set "DOWNLOAD_PATH=%RUNTIME_DIR%\%ZIP_FILENAME%"
set "DOWNLOAD_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%ZIP_FILENAME%"
set "NO_PAUSE="
set "SKIP_AUTH="

rem --no-pause means non-interactive bootstrap (keeps existing automated smoke safe).
rem --skip-auth installs dependencies but does not access the TradingView account.
:parse_arguments
if "%~1"=="" goto :arguments_ready
if /I "%~1"=="--no-pause" (
    set "NO_PAUSE=1"
    set "SKIP_AUTH=1"
    shift
    goto :parse_arguments
)
if /I "%~1"=="--skip-auth" (
    set "SKIP_AUTH=1"
    shift
    goto :parse_arguments
)
echo 不明なオプションです。通常は引数なしでダブルクリックしてください。
echo 対応オプション: --no-pause  --skip-auth
exit /b 2

:arguments_ready
echo.
echo ================================================================
echo   TradingView MCP Support セットアップ
echo ================================================================
echo.
echo このセットアップは、Pythonの準備からTradingViewのログインまで行います。
echo システムPythonのインストールや管理者権限は不要です。
echo 初回はインターネット接続とTradingView公式MCP対応プランが必要です。
echo ブラウザが開いたら、TradingViewでログインしてアクセスを許可してください。
echo.
if defined SKIP_AUTH echo 非対話・セットアップ専用モードです。ブラウザ認証は起動しません。
echo.

for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set "PTH_FILENAME=python%%a%%b._pth"
    set "STDLIB_FILENAME=python%%a%%b.zip"
    set "DLL_FILENAME=python%%a%%b.dll"
)

cd /d "%~dp0"
if errorlevel 1 goto :error

set "SETUP_STEP=Python 3.12.8の導入"
echo [1/3] Python %PYTHON_VERSION% と実行環境を準備しています。
echo 保存先: %TARGET_DIR%
echo.

if not exist "%RUNTIME_DIR%\" mkdir "%RUNTIME_DIR%"
if errorlevel 1 goto :error

set "RUNTIME_HEALTHY="
if exist "%TARGET_DIR%\python.exe" if exist "%TARGET_DIR%\%PTH_FILENAME%" if exist "%TARGET_DIR%\%STDLIB_FILENAME%" if exist "%TARGET_DIR%\%DLL_FILENAME%" (
    "%TARGET_DIR%\python.exe" -I -c "import sys, encodings, ssl, pathlib; assert '.'.join(map(str, sys.version_info[:3])) == '%PYTHON_VERSION%'; assert any(line.strip() in ('#import site', 'import site') for line in pathlib.Path(sys.executable).with_name('%PTH_FILENAME%').read_text().splitlines())" >nul 2>&1
    if not errorlevel 1 set "RUNTIME_HEALTHY=1"
)

if defined RUNTIME_HEALTHY (
    echo インストール済みのPythonを再利用します。
) else (
    if exist "%TARGET_DIR%\" (
        echo Python環境に不足があるため、Python本体のみ修復します。
        rmdir /s /q "%TARGET_DIR%"
        if exist "%TARGET_DIR%\" goto :error
    )

    if exist "%DOWNLOAD_PATH%" del /q "%DOWNLOAD_PATH%" >nul 2>&1

    echo Python本体を公式サイトから取得しています。
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
    echo pipを導入しています。
    if exist "%TARGET_DIR%\get-pip.py" del /q "%TARGET_DIR%\get-pip.py" >nul 2>&1
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%TARGET_DIR%\get-pip.py'"
    if errorlevel 1 goto :error

    "%PYTHON_EXECUTABLE%" "%TARGET_DIR%\get-pip.py"
    if errorlevel 1 goto :error

    del /q "%TARGET_DIR%\get-pip.py" >nul 2>&1
)

echo ビルド用ツールを準備しています。
"%PYTHON_EXECUTABLE%" -m pip install "setuptools>=75,<81"
if errorlevel 1 goto :error

echo アプリの実行に必要なライブラリを導入しています。
rem Embeddable Python uses pythonXY._pth isolated mode.
rem pip build isolation relies on temporary paths that this runtime does not inherit reliably,
rem so build requirements are installed above and the local project is built without isolation.
"%PYTHON_EXECUTABLE%" -m pip install --no-build-isolation -r requirements.txt
if errorlevel 1 goto :error

echo.
echo アプリが起動できることを確認しています。
call "%~dp0app.bat" --help >nul
if errorlevel 1 goto :error

echo.
if defined SKIP_AUTH goto :setup_complete_without_auth

set "SETUP_STEP=TradingViewの認証状態の確認"
echo [2/3] TradingView公式MCPのログイン状態を確認しています。
rem A first-time user's missing token returns AUTH_REQUIRED / exit 3: this is expected.
rem Keep the first status probe quiet so users do not mistake expected JSON for an error.
call "%~dp0app.bat" mcp status >nul 2>&1
set "MCP_STATUS_EXIT=%errorlevel%"
if "%MCP_STATUS_EXIT%"=="0" goto :already_authenticated
if "%MCP_STATUS_EXIT%"=="3" goto :start_oauth
set "SETUP_EXIT_CODE=%MCP_STATUS_EXIT%"
echo MCPサーバーとの接続に失敗しました。
echo ネットワーク、TradingViewの利用権限、公式サーバーの状態を確認してください。
echo 詳細は app.bat mcp status を実行すると確認できます。
goto :error

:already_authenticated
echo 既存のTradingView認証を利用します。ブラウザの再ログインは不要です。
goto :verify_mcp

:start_oauth
set "SETUP_STEP=TradingView初回ブラウザ認証"
echo.
echo TradingViewの初回ログインが必要です。
echo これから既定のブラウザが開きます。
echo 画面の案内に従ってTradingViewへログインし、アクセスを許可してください。
echo ブラウザ操作が完了すると、この画面に戻ります。
echo.
call "%~dp0app.bat" mcp auth
if errorlevel 1 (
    set "SETUP_EXIT_CODE=1"
    echo TradingViewの認証に失敗しました。
    echo ブラウザの認可画面、利用プラン、通信環境を確認してください。
    echo 認証情報を削除せず、このBATを再実行できます。
    goto :error
)

:verify_mcp
set "SETUP_STEP=MCP接続とTool一覧の確認"
echo.
echo [3/3] TradingView公式MCPへの接続を検証しています。
call "%~dp0app.bat" mcp status >nul
if errorlevel 1 (
    set "SETUP_EXIT_CODE=1"
    echo 認証情報を保存した後のMCP接続確認に失敗しました。
    echo 詳細は app.bat mcp status で確認できます。
    goto :error
)
call "%~dp0app.bat" mcp tools >nul
if errorlevel 1 (
    set "SETUP_EXIT_CODE=1"
    echo TradingView公式MCPのTool一覧を取得できませんでした。
    echo 詳細は app.bat mcp tools で確認できます。
    goto :error
)
echo 認証とTool一覧の取得に成功しました。
goto :setup_success

:setup_complete_without_auth
echo [2/3] --no-pause または --skip-auth が指定されたため、ブラウザ認証を省略しました。
echo 初回利用時は setup.bat を引数なしで実行するとログインできます。

:setup_success
echo.
echo ================================================================
echo   セットアップが完了しました。
echo ================================================================
echo.
if not defined SKIP_AUTH echo TradingView公式MCPを利用する準備が整いました。
echo 通常の操作は app.bat から実行できます。
echo 設定や利用方法は docs\WINDOWS_SETUP.md を参照してください。
echo.
call :pause_if_needed
exit /b 0

:error
if not defined SETUP_EXIT_CODE set "SETUP_EXIT_CODE=%errorlevel%"
if "%SETUP_EXIT_CODE%"=="0" set "SETUP_EXIT_CODE=1"
echo.
echo ================================================================
echo   セットアップが完了しませんでした。
echo   停止箇所: %SETUP_STEP%
echo   終了コード: %SETUP_EXIT_CODE%
echo ================================================================
echo 画面のメッセージを確認してください。必要なファイルや認証情報は削除しません。
echo 問題を解消したあと、同じsetup.batを再度ダブルクリックできます。
echo.
call :pause_if_needed
exit /b %SETUP_EXIT_CODE%

:pause_if_needed
if not defined NO_PAUSE (
    echo この画面を閉じるには何かキーを押してください。
    pause >nul
)
exit /b 0
