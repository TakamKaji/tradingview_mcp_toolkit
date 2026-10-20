"""Offline tests for the allowlisted independent-history public source candidate."""
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "public_snapshot", ROOT / "scripts" / "prepare_public_snapshot.py"
)
assert SPEC and SPEC.loader
snapshot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snapshot)

USER_DOCS = (
    "README.md", "WINDOWS_SETUP.md", "SCREENING_MANUAL.md", "RESULTS.md",
    "WATCHLIST_SYNC.md", "SCHEDULE_MANUAL.md", "AI_USAGE.md",
    "TROUBLESHOOTING.md",
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args], check=True, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


@pytest.fixture
def sample_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = tmp_path / "private"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    files: dict[str, bytes] = {
        "LICENSE": b"MIT\n",
        "pyproject.toml": b'[project]\nname = "test"\nversion = "0.1.0b1"\n',
        "requirements.txt": b"-e .\n",
        "setup.bat": b"@echo off\r\n",
        "setup-runtime.bat": b"@echo off\r\n",
        "app.bat": b"@echo off\r\n",
        "setenv.bat": b"@echo off\r\n",
        "scripts/setup-ui.ps1": b"\xef\xbb\xbfWrite-Host 'test'\r\n",
        "jobs/us_sector_morning.json": b'{"enabled": false}',
        "jobs/public_sample_screen_daily.json": (
            b'{"enabled": false, "output": {"watchlistSync": false}}'
        ),
        "src/tradingview_screening/__init__.py": b"__version__ = '0.1.0b1'\n",
        "screenings/sample.json": b'{"name": "sample"}',
    }
    for name in USER_DOCS:
        files[f"docs/user/{name}"] = f"# {name}\n".encode("utf-8")
    files["docs/user/WINDOWS_SETUP.md"] += (
        b"[Old internal guide](../development/README.md)\n"
        b"[Private repo](https://github.com/TakamKaji/tradingview_mcp_support/issues/1)\n"
        b"[Valid link](RESULTS.md)\n"
    )
    for path, contents in files.items():
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(contents)
    (repo / "docs/development").mkdir(parents=True)
    (repo / "docs/development/TRADINGVIEW_MCP_OFFICIAL_REFERENCE.md").write_text(
        "third-party-copyright-copy", encoding="utf-8"
    )
    (repo / "tests/fixtures").mkdir(parents=True)
    (repo / "tests/fixtures/provider.json").write_text(
        "third-party-provider-description", encoding="utf-8"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "Initial private commit")
    monkeypatch.setattr(snapshot, "SOURCE_PATHS", frozenset(files))
    return repo


def test_snapshot_has_no_git_history_or_excluded_copyright(sample_repo: Path) -> None:
    first = sample_repo.parent / "out-first"
    second = sample_repo.parent / "out-second"
    count, version = snapshot.build_snapshot(sample_repo, first)
    count2, version2 = snapshot.build_snapshot(sample_repo, second)
    assert (count, version) == (count2, version2)
    assert version == "0.1.0b1"
    assert not (first / ".git").exists()
    assert not (first / "tests").exists()
    assert not (first / "docs/development").exists()
    assert not (first / "docs/archive").exists()
    assert b"third-party-copyright-copy" not in (first / "README.md").read_bytes()
    assert (first / "scripts/setup-ui.ps1").read_bytes().startswith(b"\xef\xbb\xbf")
    manifest = (first / snapshot.MANIFEST_PATH).read_bytes()
    assert manifest == (second / snapshot.MANIFEST_PATH).read_bytes()
    assert "commit" not in manifest.decode("utf-8").lower()
    assert json.loads(manifest)["version"] == version


def test_private_links_and_missing_links_become_plain_text(sample_repo: Path) -> None:
    output = sample_repo.parent / "sanitized"
    snapshot.build_snapshot(sample_repo, output)
    contents = (output / "docs/user/WINDOWS_SETUP.md").read_text(encoding="utf-8")
    assert "Old internal guide" in contents
    assert "(../development/" not in contents
    assert "github.com/TakamKaji/tradingview_mcp_support" not in contents
    assert "[Valid link](RESULTS.md)" in contents


def test_existing_output_is_never_overwritten(sample_repo: Path) -> None:
    output = sample_repo.parent / "exists"
    output.mkdir()
    (output / "DO_NOT_DELETE.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError, match="already exists"):
        snapshot.build_snapshot(sample_repo, output)
    assert (output / "DO_NOT_DELETE.txt").read_text(encoding="utf-8") == "keep"


def test_credential_like_pattern_is_rejected(sample_repo: Path) -> None:
    unsafe = sample_repo / "docs/user/WINDOWS_SETUP.md"
    with unsafe.open("a", encoding="utf-8") as file:
        file.write("\nghp_" + "A" * 30)
    _git(sample_repo, "add", "-A")
    _git(sample_repo, "commit", "-m", "Unsafe accidental paste")
    with pytest.raises(ValueError, match="Credential-like"):
        snapshot.build_snapshot(sample_repo, sample_repo.parent / "unsafe")
    assert not (sample_repo.parent / "unsafe").exists()


def test_git_tracked_symlink_is_rejected(sample_repo: Path) -> None:
    link = sample_repo / "docs/user/AI_USAGE.md"
    link.unlink()
    try:
        link.symlink_to("RESULTS.md")
    except (OSError, NotImplementedError):
        pytest.skip("Current environment cannot create symlinks")
    _git(sample_repo, "add", "-A")
    _git(sample_repo, "commit", "-m", "Symlink")
    with pytest.raises(ValueError, match="Non-regular"):
        snapshot.build_snapshot(sample_repo, sample_repo.parent / "symlink")


def test_no_write_enabled_in_public_job(sample_repo: Path) -> None:
    unsafe = sample_repo / "jobs/public_sample_screen_daily.json"
    unsafe.write_text(
        '{"enabled": false, "output": {"watchlistSync": true}}', encoding="utf-8"
    )
    _git(sample_repo, "add", "-A")
    _git(sample_repo, "commit", "-m", "Unsafe Job")
    with pytest.raises(ValueError, match="watchlist"):
        snapshot.build_snapshot(sample_repo, sample_repo.parent / "badjob")
