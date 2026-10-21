@echo off
setlocal enabledelayedexpansion

rem カレントディレクトリをこのファイルの場所に固定
cd /d "%~dp0"

rem 文字コードをUTF-8に設定
chcp 65001 >nul

rem ポータブルPython環境の読み込み (ループの外で1回だけ実行する)
call "%~dp0setenv.bat"

:MAIN_MENU
cls
echo ======================================================
echo       Python Tool
echo ======================================================
echo.

rem pyフォルダ内のファイルから動的にメニューを生成
set COUNT=0
for %%f in (py\*.py) do (
    set /a COUNT+=1
    set "FILE_!COUNT!=%%~nxf"
    
    rem サブルーチンを呼び出してタイトルを取得し、MENU_TITLE変数にセット
    call :GET_MENU_TITLE "%%f"
    
    echo  [!COUNT!] !MENU_TITLE! ^(%%~nxf^)
)

echo.
echo  [0] 終了
echo.
echo ======================================================

rem 変数をクリアしてから入力を受け付ける
set CHOICE=
set /p CHOICE="実行する番号を選んでください [0-!COUNT!]: "

if "%CHOICE%"=="0" (
    echo 👋 終了します。
    exit /b 0
)

rem 選択された番号のスクリプト名を取得
set "TARGET_SCRIPT=!FILE_%CHOICE%!"

if "!TARGET_SCRIPT!"=="" (
    rem 定義されていない番号が入力された場合
    echo.
    echo ❌ 不正な入力です。もう一度入力してください。
    timeout /t 2 >nul
    goto MAIN_MENU
)

echo.
echo 🚀 !TARGET_SCRIPT! を開始します...
python py/!TARGET_SCRIPT!
goto FINISHED

:FINISHED
echo.
echo ------------------------------------------------------
echo 処理が完了しました。
pause
goto MAIN_MENU


rem ======================================================
rem サブルーチン: Pythonファイルからタイトルを抽出・トリム
rem ======================================================
:GET_MENU_TITLE
set "MENU_TITLE="
set "raw_line="
set "temp_title="

rem "# MENU_TITLE:" が含まれる行を取得
for /f "tokens=* delims=" %%A in ('findstr /c:"# MENU_TITLE:" %1 2^>nul') do (
    set "raw_line=%%A"
)

if "!raw_line!"=="" (
    set "MENU_TITLE=タイトルなし"
    exit /b
)

rem ":" で区切って右側を取得
for /f "tokens=1,* delims=:" %%a in ("!raw_line!") do (
    set "temp_title=%%b"
)

rem 先頭の空白をトリム
for /f "tokens=* delims= " %%c in ("!temp_title!") do (
    set "MENU_TITLE=%%c"
)

if "!MENU_TITLE!"=="" set "MENU_TITLE=タイトルなし"
exit /b