@echo off
setlocal EnableExtensions DisableDelayedExpansion
title TradingView MCP Support - Second PC Beta Acceptance Test

rem Standalone Windows batch: clone private PR branch, setup, OAuth, read-only checks, tests.
rem Never deletes an existing checkout, credentials, tasks, watchlists, or saved results.
rem Run as a standard Windows user. Interactive GitHub / TradingView browser login is required.
set "BRANCH=chore/issue-28-release-candidate-b1"
set "REPO=https://github.com/TakamKaji/tradingview_mcp_support.git"
set "TARGET=%USERPROFILE%\TV MCP Beta Test"
set "REPORT=%USERPROFILE%\TV_MCP_BETA_TEST_RESULT.txt"
set "STEP=initialization"
set "RESULT=FAIL"
set "AUTH_TEST=NOT_RUN"
set "SETUP_TEST=NOT_RUN"
set "READ_TEST=NOT_RUN"
set "UNIT_TEST=NOT_RUN"
set "PYTEST_SUMMARY=NOT_RUN"
set "RUFF_TEST=NOT_RUN"
set "PERSIST_TEST=NOT_RUN"
set "BASELINE_TEST=NOT_RUN"
set "GIT_SHA=UNKNOWN"
set "CAPTURE="
set "FAIL_REASON=Unknown failure"

echo.
echo ====================================================================
echo   TradingView MCP Support v0.1.0b1 - Second PC Full Acceptance Test
echo ====================================================================
echo.
echo This script will download the PRIVATE PR #29 branch into:
echo   "%TARGET%"
echo.
echo - Use a normal Windows account, NOT Run as Administrator.
echo - GitHub and TradingView login need your browser interaction.
echo - No system Python installation, Watchlist Write, or Task creation.
echo - Do not paste OAuth tokens or GitHub credentials into a report.
echo.
echo Press any key to start, or close this window to cancel.
pause >nul

set "STEP=Check PowerShell"
where powershell.exe >nul 2>&1
if errorlevel 1 (
    set "FAIL_REASON=Windows PowerShell is required."
    goto :fail
)

set "STEP=Install or find Git"
set "PATH=%ProgramFiles%\Git\cmd;%LOCALAPPDATA%\Programs\Git\cmd;%PATH%"
where git.exe >nul 2>&1
if not errorlevel 1 goto :git_ready
where winget.exe >nul 2>&1
if errorlevel 1 (
    echo Git and winget are both missing.
    echo Install Git for Windows from https://git-scm.com/downloads/win and run this BAT again.
    set "FAIL_REASON=Git is not installed and winget is unavailable."
    goto :fail
)
echo.
echo [1/8] Installing Git for Windows via winget...
winget install --id Git.Git -e --source winget --accept-source-agreements --accept-package-agreements
if errorlevel 1 (
    set "FAIL_REASON=Git installation failed. Install Git for Windows then rerun this BAT."
    goto :fail
)
set "PATH=%ProgramFiles%\Git\cmd;%LOCALAPPDATA%\Programs\Git\cmd;%PATH%"
where git.exe >nul 2>&1
if errorlevel 1 (
    set "FAIL_REASON=Git installation ended but git.exe was not found. Reopen Windows and rerun."
    goto :fail
)

:git_ready
echo.
echo [1/8] Git detected.
git --version
if errorlevel 1 (
    set "FAIL_REASON=Cannot execute git."
    goto :fail
)

set "STEP=Clone or resume checkout"
echo.
echo [2/8] Checking PR #29 checkout...
if exist "%TARGET%\.git\" goto :resume_checkout
if exist "%TARGET%\" (
    set "FAIL_REASON=Target folder exists without a Git checkout. It was not modified."
    goto :fail
)
echo Cloning PRIVATE repository. Sign in to GitHub if prompted.
git clone --branch "%BRANCH%" --single-branch "%REPO%" "%TARGET%"
if errorlevel 1 (
    set "FAIL_REASON=Git clone failed. Check browser GitHub login and private repo permission."
    goto :fail
)
goto :checkout_ready

:resume_checkout
echo Existing test checkout found. Resuming WITHOUT deleting or pulling files.
for /f "delims=" %%R in ('git -C "%TARGET%" remote get-url origin') do set "FOUND_REPO=%%R"
if /i not "%FOUND_REPO%"=="%REPO%" (
    set "FAIL_REASON=Existing checkout has an unexpected Git remote; refusing to modify it."
    goto :fail
)
for /f "delims=" %%B in ('git -C "%TARGET%" branch --show-current') do set "FOUND_BRANCH=%%B"
if /i not "%FOUND_BRANCH%"=="%BRANCH%" (
    set "FAIL_REASON=Existing checkout is on an unexpected branch; refusing to switch."
    goto :fail
)

:checkout_ready
cd /d "%TARGET%"
if errorlevel 1 (
    set "FAIL_REASON=Cannot open checkout directory."
    goto :fail
)
for /f "delims=" %%H in ('git rev-parse HEAD') do set "GIT_SHA=%%H"
set "DIRTY_CHECK="
for /f "delims=" %%D in ('git status --porcelain') do set "DIRTY_CHECK=1"
if defined DIRTY_CHECK (
    set "FAIL_REASON=Checkout has modified or untracked files. Preserve them and inspect before rerun."
    goto :fail
)
echo Branch: %BRANCH%
echo Commit: %GIT_SHA%

set "STEP=Setup Embedded Python"
echo.
echo [3/8] Installing Windows Embedded Python and runtime dependencies...
call ".\setup.bat" --no-pause
if errorlevel 1 (
    set "FAIL_REASON=setup.bat failed. Check setup output."
    goto :fail
)
call ".\app.bat" --help >nul
if errorlevel 1 (
    set "FAIL_REASON=app.bat --help failed."
    goto :fail
)
set "PYEXE=%TARGET%\runtime\python-3.12.8\python.exe"
if not exist "%PYEXE%" (
    set "FAIL_REASON=Embedded Python executable was not installed."
    goto :fail
)
"%PYEXE%" -I -c "import sys,importlib.metadata as m,tradingview_screening as t; assert sys.version_info[:3]==(3,12,8); assert sys.flags.isolated==1; assert m.version('tradingview-mcp-support')=='0.1.0b1'; assert t.__version__=='0.1.0b1'; print('PASS: Python 3.12.8 / isolated / package 0.1.0b1')"
if errorlevel 1 (
    set "FAIL_REASON=Python package/runtime version mismatch."
    goto :fail
)
"%PYEXE%" -I -c "import importlib.util as u; assert u.find_spec('pytest') is None and u.find_spec('ruff') is None; print('PASS: dev dependencies absent in clean runtime')"
if errorlevel 1 (
    set "FAIL_REASON=Development dependencies were already installed into the supposedly clean runtime."
    goto :fail
)
set "SETUP_TEST=PASS"

set "STEP=First OAuth"
echo.
echo [4/8] Checking initial TradingView authentication...
call ".\app.bat" mcp status
set "BEFORE_AUTH_RC=%errorlevel%"
if "%BEFORE_AUTH_RC%"=="3" goto :new_oauth
if "%BEFORE_AUTH_RC%"=="0" goto :existing_oauth
set "FAIL_REASON=Pre-auth status failed with unexpected exit code."
goto :fail

:new_oauth
echo PASS: Initial status returned AUTH_REQUIRED (exit 3).
echo.
echo Your BROWSER will open for initial TradingView authorization.
echo Use your own TradingView account. Do not share tokens or authorization codes.
call ".\app.bat" mcp auth
if errorlevel 1 (
    set "FAIL_REASON=Interactive first-time TradingView OAuth failed."
    goto :fail
)
set "AUTH_TEST=FIRST_OAUTH_PASS"
goto :authenticated

:existing_oauth
echo NOTE: Credential already existed for this Windows user.
echo First-time OAuth has NOT been tested here; existing auth will be reused.
set "AUTH_TEST=EXISTING_CREDENTIAL_ONLY"

:authenticated
set "STEP=MCP status and tool discovery"
call ".\app.bat" mcp status
if errorlevel 1 (
    set "FAIL_REASON=MCP status after authentication failed."
    goto :fail
)
call ".\app.bat" mcp tools
if errorlevel 1 (
    set "FAIL_REASON=MCP Tool Discovery failed."
    goto :fail
)

set "STEP=Read-only Job and history"
echo.
echo [5/8] Read-only Job, JSON save, latest/history, compare, and schedule list...
call ".\app.bat" jobs list
if errorlevel 1 (
    set "FAIL_REASON=jobs list failed."
    goto :fail
)
powershell.exe -NoProfile -NonInteractive -Command "$j = Get-Content -LiteralPath 'jobs\us_sector_morning.json' -Raw | ConvertFrom-Json; if ($j.enabled -ne $false -or $j.output.watchlistSync -ne $false) { exit 1 }; Write-Host 'PASS: us_sector_morning is disabled and read-only'"
if errorlevel 1 (
    set "FAIL_REASON=US sector Job sample is not safely disabled."
    goto :fail
)
if not exist ".local\" mkdir ".local"
set "CAPTURE=%TARGET%\.local\second_pc_test_output.tmp"
set "HAD_PREVIOUS_HISTORY=0"
if exist "results\" (
    for /r "results" %%F in (sample_standard_screen_*.json) do set "HAD_PREVIOUS_HISTORY=1"
)
if exist "%CAPTURE%" (
    set "FAIL_REASON=Old test capture exists. It was not overwritten."
    goto :fail
)

echo Running public read-only Job: first snapshot...
call ".\app.bat" run public_sample_screen_daily > "%CAPTURE%"
if errorlevel 1 (
    set "FAIL_REASON=First read-only Job failed; inspect the local capture file."
    goto :fail
)
"%PYEXE%" -c "import json,sys; j=json.load(open(sys.argv[1],encoding='utf-8')); assert j.get('status')=='success' and j.get('metadata',{}).get('saved') is True and j.get('watchlistSync') is None; print('PASS: first read-only Job succeeded and saved JSON')" "%CAPTURE%"
if errorlevel 1 (
    set "FAIL_REASON=First Job result was not success/saved/read-only."
    goto :fail
)
del /q "%CAPTURE%" >nul 2>&1

call ".\app.bat" results latest sample_standard_screen >nul
if errorlevel 1 (
    set "FAIL_REASON=results latest failed."
    goto :fail
)
call ".\app.bat" results history sample_standard_screen --limit 10 >nul
if errorlevel 1 (
    set "FAIL_REASON=results history after first Job failed."
    goto :fail
)
if "%HAD_PREVIOUS_HISTORY%"=="1" goto :skip_first_no_baseline
call ".\app.bat" results compare sample_standard_screen > "%CAPTURE%"
set "COMPARE_RC=%errorlevel%"
if not "%COMPARE_RC%"=="1" (
    set "FAIL_REASON=First compare expected NO_BASELINE/exit1."
    goto :fail
)
findstr /C:"NO_BASELINE" "%CAPTURE%" >nul
if errorlevel 1 (
    set "FAIL_REASON=First compare did not report NO_BASELINE."
    goto :fail
)
echo PASS: first compare = NO_BASELINE / exit 1.
set "BASELINE_TEST=PASS"
del /q "%CAPTURE%" >nul 2>&1
goto :first_compare_done

:skip_first_no_baseline
echo Existing snapshots were found. First-time NO_BASELINE test is skipped safely.
set "BASELINE_TEST=SKIPPED_PREVIOUS_HISTORY"

:first_compare_done
echo Running public read-only Job: second snapshot...
call ".\app.bat" run public_sample_screen_daily > "%CAPTURE%"
if errorlevel 1 (
    set "FAIL_REASON=Second read-only Job failed."
    goto :fail
)
"%PYEXE%" -c "import json,sys; j=json.load(open(sys.argv[1],encoding='utf-8')); assert j.get('status')=='success' and j.get('metadata',{}).get('saved') is True and j.get('watchlistSync') is None; print('PASS: second read-only Job succeeded and saved JSON')" "%CAPTURE%"
if errorlevel 1 (
    set "FAIL_REASON=Second Job result was not success/saved/read-only."
    goto :fail
)
del /q "%CAPTURE%" >nul 2>&1

call ".\app.bat" results history sample_standard_screen --limit 10 >nul
if errorlevel 1 (
    set "FAIL_REASON=results history after second Job failed."
    goto :fail
)
call ".\app.bat" results compare sample_standard_screen > "%CAPTURE%"
if errorlevel 1 (
    set "FAIL_REASON=Two-snapshot comparison failed."
    goto :fail
)
"%PYEXE%" -c "import json,sys; j=json.load(open(sys.argv[1],encoding='utf-8')); assert j.get('status')=='success'; print('PASS: two-snapshot comparison succeeded')" "%CAPTURE%"
if errorlevel 1 (
    set "FAIL_REASON=Two-snapshot comparison did not report success."
    goto :fail
)
del /q "%CAPTURE%" >nul 2>&1

call ".\app.bat" schedule list >nul
if errorlevel 1 (
    set "FAIL_REASON=Read-only scheduler list failed."
    goto :fail
)
set "READ_TEST=PASS"

set "STEP=Install development dependencies and run full tests"
echo.
echo [6/8] Installing development-only pytest and ruff into Embedded Python...
"%PYEXE%" -m pip install --no-build-isolation -r requirements-dev.txt
if errorlevel 1 (
    set "FAIL_REASON=Development dependency installation failed."
    goto :fail
)
echo.
echo Running complete pytest suite. Skips due to symlink permission must be reviewed.
set "PYTEST_CAPTURE=%TARGET%\.local\second_pc_pytest.log"
"%PYEXE%" -m pytest -rs > "%PYTEST_CAPTURE%" 2>&1
set "PYTEST_RC=%errorlevel%"
type "%PYTEST_CAPTURE%"
for /f "delims=" %%L in ('findstr /C:" passed" "%PYTEST_CAPTURE%"') do set "PYTEST_SUMMARY=%%L"
if not "%PYTEST_RC%"=="0" (
    set "FAIL_REASON=pytest failed. Review traceback above. A local pytest log was preserved."
    goto :fail
)
set "UNIT_TEST=PASS"
echo.
echo Running ruff...
"%PYEXE%" -m ruff check .
if errorlevel 1 (
    set "FAIL_REASON=ruff check failed."
    goto :fail
)
git diff --check
if errorlevel 1 (
    set "FAIL_REASON=git diff --check failed."
    goto :fail
)
set "DIRTY_CHECK="
for /f "delims=" %%D in ('git status --porcelain') do set "DIRTY_CHECK=1"
if defined DIRTY_CHECK (
    set "FAIL_REASON=Working tree changed during test. Investigate before release."
    goto :fail
)
set "RUFF_TEST=PASS"

set "STEP=Verify persisted OAuth in a new application process"
echo.
echo [7/8] Checking OAuth persistence in another CLI process...
call ".\app.bat" mcp status >nul
if errorlevel 1 (
    set "FAIL_REASON=OAuth was not available in a later process."
    goto :fail
)
call ".\app.bat" mcp tools >nul
if errorlevel 1 (
    set "FAIL_REASON=Tools unavailable in later process."
    goto :fail
)
set "PERSIST_TEST=PASS"
set "RESULT=PASS"
if /i "%AUTH_TEST%"=="EXISTING_CREDENTIAL_ONLY" set "RESULT=PARTIAL"
set "FAIL_REASON=None"
goto :finish

:fail
echo.
echo ============================================================
echo FAIL at step: %STEP%
echo Reason: %FAIL_REASON%
echo Stop here; do not overwrite or delete an existing checkout.
echo ============================================================
goto :finish

:finish
echo.
echo [8/8] Writing a brief result report without OAuth tokens...
> "%REPORT%" echo TradingView MCP Support - Second PC Beta Acceptance Test
>> "%REPORT%" echo Result: %RESULT%
>> "%REPORT%" echo Git branch: %BRANCH%
>> "%REPORT%" echo Git HEAD: %GIT_SHA%
>> "%REPORT%" echo Checkout: %TARGET%
>> "%REPORT%" echo Setup: %SETUP_TEST%
>> "%REPORT%" echo First OAuth: %AUTH_TEST%
>> "%REPORT%" echo Read-only screening and history: %READ_TEST%
>> "%REPORT%" echo Initial NO_BASELINE comparison: %BASELINE_TEST%
>> "%REPORT%" echo pytest: %UNIT_TEST%
>> "%REPORT%" echo pytest summary: %PYTEST_SUMMARY%
>> "%REPORT%" echo ruff and git diff check: %RUFF_TEST%
>> "%REPORT%" echo OAuth persistence: %PERSIST_TEST%
>> "%REPORT%" echo Failed step: %STEP%
>> "%REPORT%" echo Reason: %FAIL_REASON%
>> "%REPORT%" echo Note: pytest log remains in the local ignored .local folder.
echo.
echo -----------------------------------------
type "%REPORT%"
echo -----------------------------------------
echo Result file: "%REPORT%"
echo.
echo Paste this brief report and pytest totals into ChatGPT.
echo Do NOT paste OAuth tokens, private credentials, or raw authentication output.
echo.
pause
if /i "%RESULT%"=="PASS" exit /b 0
if /i "%RESULT%"=="PARTIAL" exit /b 0
exit /b 1
