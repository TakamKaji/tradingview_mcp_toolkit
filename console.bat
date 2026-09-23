@echo off
setlocal
title Tool Console

rem 環境変数を読み込む（現在のフォルダを基準にする）
call "%~dp0setenv.bat"

rem カレントディレクトリをこのバッチファイルがある場所（プロジェクトルート）に固定
cd /d "%~dp0"

echo ========================================================
echo  Python Portable Tool
echo ========================================================
echo.
echo  [Usage]
echo  Run script:  python py/***.py
echo.

rem コマンドプロンプトを開いたままにする
cmd /k