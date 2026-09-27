from pathlib import Path

from tradingview_screening import __version__
from tradingview_screening.__main__ import build_parser

ROOT = Path(__file__).resolve().parents[1]


def test_package_version_is_defined() -> None:
    assert __version__ == "0.0.0"


def test_cli_parser_can_be_built() -> None:
    parser = build_parser()
    assert parser.prog == "tradingview_screening"


def test_windows_setup_uses_pinned_embedded_python_and_shared_entrypoint() -> None:
    setup = (ROOT / "setup.bat").read_text(encoding="utf-8")

    assert 'set "PYTHON_VERSION=3.12.8"' in setup
    assert "python-%PYTHON_VERSION%-embed-%ARCH%.zip" in setup
    assert 'call "%~dp0setenv.bat"' in setup
    assert 'call "%~dp0app.bat" --help >nul' in setup


def test_windows_setup_recovers_incomplete_runtime_and_supports_noninteractive_use() -> None:
    setup = (ROOT / "setup.bat").read_text(encoding="utf-8")

    assert 'if /I "%~1"=="--no-pause" set "NO_PAUSE=1"' in setup
    assert 'if exist "%TARGET_DIR%\\python.exe"' in setup
    assert 'rmdir /s /q "%TARGET_DIR%"' in setup
    assert "if not defined NO_PAUSE pause" in setup


def test_app_entrypoint_never_falls_back_to_system_python() -> None:
    app = (ROOT / "app.bat").read_text(encoding="utf-8")

    assert 'call "%~dp0setenv.bat"' in app
    assert 'if not exist "%PYTHON_EXECUTABLE%"' in app
    assert '"%PYTHON_EXECUTABLE%" -m tradingview_screening %*' in app
