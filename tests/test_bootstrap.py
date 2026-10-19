import os
import subprocess
import sys
from pathlib import Path

import pytest

from tradingview_screening import __version__
from tradingview_screening.__main__ import build_parser

ROOT = Path(__file__).resolve().parents[1]


def test_package_version_is_defined() -> None:
    assert __version__ == "0.1.0b1"


def test_windows_release_install_does_not_install_dev_extras() -> None:
    runtime = (ROOT / "requirements.txt").read_text(encoding="utf-8").strip()
    dev = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8").strip()
    setup = (ROOT / "setup-runtime.bat").read_text(encoding="utf-8")
    assert runtime == "-e ."
    assert dev == "-e .[dev]"
    assert 'pip install --no-build-isolation -r requirements.txt' in setup
    assert 'pip install --no-build-isolation -r requirements-dev.txt' not in setup


def test_cli_parser_can_be_built() -> None:
    parser = build_parser()
    assert parser.prog == "tradingview_screening"


def test_windows_setup_uses_pinned_embedded_python_and_shared_entrypoint() -> None:
    setup = (ROOT / "setup-runtime.bat").read_text(encoding="ascii")

    assert 'set "PYTHON_VERSION=3.12.8"' in setup
    assert "python-%PYTHON_VERSION%-embed-%ARCH%.zip" in setup
    assert 'call "%~dp0setenv.bat"' in setup
    assert 'call "%~dp0app.bat" --help >nul' in setup


def test_windows_setup_recovers_incomplete_runtime_and_supports_noninteractive_use() -> None:
    setup = (ROOT / "setup-runtime.bat").read_text(encoding="ascii")

    assert 'if /I "%~1"=="--no-pause" set "NO_PAUSE=1"' in setup
    assert 'if exist "%TARGET_DIR%\\python.exe"' in setup
    assert 'if exist "%TARGET_DIR%\\%PTH_FILENAME%"' in setup
    assert 'if exist "%TARGET_DIR%\\%STDLIB_FILENAME%"' in setup
    assert 'if exist "%TARGET_DIR%\\%DLL_FILENAME%"' in setup
    assert '"%TARGET_DIR%\\python.exe" -I -c "import sys, encodings, ssl, pathlib;' in setup
    assert 'if defined RUNTIME_HEALTHY (' in setup
    assert 'rmdir /s /q "%TARGET_DIR%"' in setup
    assert 'rmdir /s /q "%APP_LOCAL_DIR%"' not in setup
    assert 'set "PTH_FILEPATH=%TARGET_DIR%\\%PTH_FILENAME%"' in setup
    assert "Always enable site on rerun" in setup
    assert "$path = $env:PTH_FILEPATH" in setup
    assert "if ($content -notmatch '(?m)^import site[ \\t]*\\r?$')" in setup


def test_click_setup_uses_ascii_batch_and_bom_power_shell_ui() -> None:
    launcher = (ROOT / "setup.bat").read_bytes()
    ui_bytes = (ROOT / "scripts/setup-ui.ps1").read_bytes()
    assert launcher.isascii()  # Windows cmd must never parse UTF-8 Japanese.
    assert b"powershell.exe -NoProfile -ExecutionPolicy Bypass -File" in launcher
    assert b"scripts\\setup-ui.ps1" in launcher
    assert ui_bytes.startswith(b"\xef\xbb\xbf")
    ui = ui_bytes.decode("utf-8-sig")
    assert "TradingView" in ui
    assert "初回ログインが必要です" in ui
    assert "$AuthStatus -eq 3" in ui
    assert "$AuthStatus -eq 0" in ui
    assert "@('mcp','auth')" in ui
    assert "@('mcp','status')" in ui
    assert "@('mcp','tools')" in ui
    assert "'--no-pause' { $NoPause = $true; $SkipAuth = $true }" in ui
    assert "'--skip-auth' { $SkipAuth = $true }" in ui
    assert "setup-runtime.bat" in ui
    assert "schedule apply" not in ui
    assert "run sample_screen_daily" not in ui



@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell script parser")
def test_powershell_ui_has_valid_syntax(tmp_path: Path) -> None:
    script = ROOT / "scripts/setup-ui.ps1"
    env = {**os.environ, "SETUP_UI_SCRIPT_PATH": str(script)}
    check = (
        "$tokens=$null; $errors=$null; "
        "[void][System.Management.Automation.Language.Parser]::ParseFile("
        "$env:SETUP_UI_SCRIPT_PATH, [ref]$tokens, [ref]$errors); "
        "if ($errors.Count -gt 0) { $errors | Out-String | Write-Error; exit 1 }"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", check],
        cwd=tmp_path, env=env, capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_app_entrypoint_never_falls_back_to_system_python() -> None:
    app = (ROOT / "app.bat").read_text(encoding="utf-8")

    assert 'call "%~dp0setenv.bat"' in app
    assert 'if not exist "%PYTHON_EXECUTABLE%"' in app
    assert '"%PYTHON_EXECUTABLE%" -m tradingview_screening %*' in app


def test_setenv_preserves_windows_user_profile_and_credentials() -> None:
    setenv = (ROOT / "setenv.bat").read_text(encoding="utf-8")
    for name in ("USERPROFILE", "HOME", "HOMEPATH", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP"):
        assert f'set "{name}=' not in setenv
    assert 'set "PYTHONHOME="' in setenv
    assert 'set "PYTHONPATH="' in setenv


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell bootstrap")
@pytest.mark.parametrize("newline", ["\r\n", "\n"])
def test_site_repair_handles_embedded_pth_line_endings(tmp_path: Path, newline: str) -> None:
    setup = (ROOT / "setup-runtime.bat").read_text(encoding="ascii")
    command = next(
        line.strip()[1:-1] for line in setup.splitlines()
        if line.strip().startswith('"$path = $env:PTH_FILEPATH;')
    )
    pth = tmp_path / "python312._pth"
    original = newline.join(("python312.zip", ".", "#import site", ""))
    pth.write_bytes(original.encode("ascii"))
    environment = {**os.environ, "PTH_FILEPATH": str(pth)}
    for _ in range(2):  # The repair must be safe when setup is rerun.
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            env=environment, capture_output=True, text=True, check=False,
        )
        assert completed.returncode == 0, completed.stderr
        assert pth.read_bytes() == original.replace("#import site", "import site").encode("ascii")
