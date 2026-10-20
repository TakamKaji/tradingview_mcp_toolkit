#!/usr/bin/env python3
"""Prepare an offline, history-free public source candidate from a private Git commit.

This is NOT a publication, permission grant, or substitute for manual review.
It never performs git init, git push, GitHub API requests, OAuth, or network calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import re
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path
from urllib.parse import unquote

# Exact, reviewed paths. New source files MUST be intentionally added here.
# Third-party documentation copies, provider schema fixtures, tests needing
# these fixtures, private development notes and entire Git history are omitted.
SOURCE_PATHS = frozenset(
    (
    "LICENSE",
    "app.bat",
    "docs/user/AI_USAGE.md",
    "docs/user/README.md",
    "docs/user/RESULTS.md",
    "docs/user/SCHEDULE_MANUAL.md",
    "docs/user/SCREENING_MANUAL.md",
    "docs/user/TROUBLESHOOTING.md",
    "docs/user/WATCHLIST_SYNC.md",
    "docs/user/WINDOWS_SETUP.md",
    "jobs/public_japan_value_daily.json",
    "jobs/public_oversold_healthy_daily.json",
    "jobs/public_sample_screen_daily.json",
    "jobs/public_sp500_daily.json",
    "jobs/public_sp500_symbolset_daily.json",
    "jobs/sample_screen_daily.json",
    "jobs/us_sector_morning.json",
    "pyproject.toml",
    "requirements.txt",
    "screenings/public_japan_value.json",
    "screenings/public_oversold_healthy.json",
    "screenings/public_sp500.json",
    "screenings/public_sp500_symbolset.json",
    "screenings/sample_standard_screen.json",
    "scripts/setup-ui.ps1",
    "setenv.bat",
    "setup-runtime.bat",
    "setup.bat",
    "src/tradingview_screening/__init__.py",
    "src/tradingview_screening/__main__.py",
    "src/tradingview_screening/common/__init__.py",
    "src/tradingview_screening/common/config.py",
    "src/tradingview_screening/common/errors.py",
    "src/tradingview_screening/common/request_governor.py",
    "src/tradingview_screening/integrations/__init__.py",
    "src/tradingview_screening/integrations/tradingview/__init__.py",
    "src/tradingview_screening/integrations/tradingview/auth.py",
    "src/tradingview_screening/integrations/tradingview/client.py",
    "src/tradingview_screening/integrations/tradingview/oauth_bootstrap.py",
    "src/tradingview_screening/integrations/tradingview/schemas.py",
    "src/tradingview_screening/integrations/tradingview/screener_normalization.py",
    "src/tradingview_screening/integrations/tradingview/tool_catalog.py",
    "src/tradingview_screening/integrations/tradingview/us_sector_normalization.py",
    "src/tradingview_screening/integrations/tradingview/watchlist_normalization.py",
    "src/tradingview_screening/jobs/__init__.py",
    "src/tradingview_screening/jobs/builtin.py",
    "src/tradingview_screening/jobs/loader.py",
    "src/tradingview_screening/jobs/runner.py",
    "src/tradingview_screening/jobs/scheduler.py",
    "src/tradingview_screening/jobs/schema.py",
    "src/tradingview_screening/jobs/us_sector.py",
    "src/tradingview_screening/screening/__init__.py",
    "src/tradingview_screening/screening/comparison.py",
    "src/tradingview_screening/screening/engine.py",
    "src/tradingview_screening/screening/fingerprint.py",
    "src/tradingview_screening/screening/managed_watchlists.py",
    "src/tradingview_screening/screening/results.py",
    "src/tradingview_screening/screening/schema.py",
    "src/tradingview_screening/screening/validators.py",
    "src/tradingview_screening/screening/watchlist_sync.py",
    )
)
GENERATED_PATHS = frozenset({"README.md", "docs/README.md", "docs/WINDOWS_SETUP.md", ".gitignore"})
MANIFEST_PATH = "PUBLIC_SOURCE_MANIFEST.json"
MD_LINK = re.compile(r"(?<!!)\[([^\]\n]+)\]\(([^)\n]+)\)")
PRIVATE_URL_PARTS = (
    "github.com/takamkaji/tradingview_mcp_support",
    "drive.google.com/",
    "app.notion.com/",
)
SECRET_PATTERNS = (
    re.compile(r"(?i)github_pat_[a-z0-9_]{20,}"),
    re.compile(r"(?i)gh[pousr]_[a-z0-9_]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
EMAIL_PATTERN = re.compile(r"(?i)[a-z0-9._%+-]+@([a-z0-9.-]+\.[a-z]{2,})")
EMAIL_EXAMPLE_DOMAINS = {"example.com", "example.org", "example.net", "invalid.test"}


def git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, check=False
    )
    if result.returncode:
        # stderr could contain sensitive paths/data; never echo it.
        raise ValueError("Git operation failed. Check local repository and revision.")
    return result.stdout


def source_blobs(repo: Path, ref: str) -> dict[str, str]:
    commit = git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}").decode().strip()
    records = git(repo, "ls-tree", "-r", "-z", "--full-tree", commit)
    blobs: dict[str, str] = {}
    for record in records.split(b"\0"):
        if not record:
            continue
        metadata, name_bytes = record.split(b"\t", 1)
        mode, kind, object_id = metadata.decode("ascii").split()
        name = name_bytes.decode("utf-8")
        if name not in SOURCE_PATHS:
            continue
        if mode not in {"100644", "100755"} or kind != "blob":
            raise ValueError(f"Non-regular source file rejected: {name}")
        blobs[name] = object_id
    absent = sorted(SOURCE_PATHS - blobs.keys())
    if absent:
        raise ValueError(f"Reviewed source path missing: {absent[0]}")
    return blobs


def markdown_link_target_exists(path: str, link: str, included: set[str]) -> bool:
    if link.startswith(("https://", "http://", "mailto:", "#")):
        return True
    target = unquote(link.split("#", 1)[0].split("?", 1)[0])
    if not target:
        return True
    if target.startswith("/"):
        return False
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), target))
    if resolved == ".." or resolved.startswith("../"):
        return False
    return resolved in included or any(x.startswith(resolved.rstrip("/") + "/") for x in included)


def clean_markdown(path: str, source: bytes, included: set[str]) -> bytes:
    text = source.decode("utf-8-sig")
    def replace(match: re.Match[str]) -> str:
        label, url = match.groups()
        normalized = url.lower()
        if any(part in normalized for part in PRIVATE_URL_PARTS):
            return label
        if not markdown_link_target_exists(path, url, included):
            return label
        return match.group(0)
    text = MD_LINK.sub(replace, text)
    # This is a release candidate, not the old private checkout.
    text = text.replace("Privateリポジトリ", "配布元リポジトリ")
    text = text.replace("現在Private", "公開準備中")
    text = text.replace("TakamKaji/tradingview_mcp_support", "公開用リポジトリ")
    return text.encode("utf-8")


def check_text(path: str, contents: bytes) -> None:
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeError as error:
        raise ValueError(f"Non-UTF-8 content rejected: {path}") from error
    lower = text.lower()
    if any(part in lower for part in PRIVATE_URL_PARTS):
        raise ValueError(f"Private destination reference rejected: {path}")
    if any(pattern.search(text) for pattern in SECRET_PATTERNS):
        raise ValueError(f"Credential-like pattern rejected: {path}")
    for match in EMAIL_PATTERN.finditer(text):
        if match.group(1).lower() not in EMAIL_EXAMPLE_DOMAINS:
            raise ValueError(f"Non-example email address needs review: {path}")


def make_readme(version: str) -> bytes:
    return f"""# TradingView MCP Support

TradingView公式MCPの非公式サポートツールです。TradingView社と提携・承認関係はありません。

WindowsではPythonの事前インストールや管理者権限は不要です。

## 導入

1. 公開元が案内する配布ZIPをダウンロードして展開します。
2. 展開したフォルダ内の setup.bat をダブルクリックします。
3. 未認証ならブラウザでTradingViewにログイン・許可します。
4. 接続確認が成功したら、コマンドプロンプトで以下を実行できます。

    app.bat run public_sample_screen_daily
    app.bat results latest sample_standard_screen

上記はTradingViewのReadとローカル結果保存のみ。WatchlistへWriteせず、
Windows Task Schedulerへ登録しません。

## マニュアル

- [Windows導入・認証](docs/user/WINDOWS_SETUP.md)
- [Screening](docs/user/SCREENING_MANUAL.md)
- [保存結果・前回比較](docs/user/RESULTS.md)
- [Watchlist同期（Write）](docs/user/WATCHLIST_SYNC.md)
- [Task Scheduler](docs/user/SCHEDULE_MANUAL.md)
- [トラブルシューティング](docs/user/TROUBLESHOOTING.md)
- [マニュアル一覧](docs/README.md)

TradingView公式MCPはBetaで、全米株を条件なしで取得する方式は未対応です。
us_sector_morning は既定で無効です。

Version: {version}。このソース候補は公開済みRelease・公開許諾を意味しません。
MIT License。第三者ライブラリ／資料には別途権利条件が適用されます。
""".encode("utf-8")


def make_docs_index() -> bytes:
    return """# 利用者マニュアル

- [Windows導入と認証](user/WINDOWS_SETUP.md)
- [Screening](user/SCREENING_MANUAL.md)
- [結果・履歴・比較](user/RESULTS.md)
- [Watchlist（実Writeあり）](user/WATCHLIST_SYNC.md)
- [Scheduler（Task登録・削除あり）](user/SCHEDULE_MANUAL.md)
- [AIからのCLI利用](user/AI_USAGE.md)
- [トラブル対応](user/TROUBLESHOOTING.md)

この公開候補にはPrivate開発リポジトリの設計履歴・監査資料を収録していません。
[最初に戻る](../README.md)
""".encode("utf-8")


def validate_snapshot(contents: dict[str, bytes]) -> str:
    metadata = tomllib.loads(contents["pyproject.toml"].decode("utf-8"))
    version = metadata["project"]["version"]
    if not isinstance(version, str) or not re.fullmatch(r"[0-9A-Za-z.+-]+", version):
        raise ValueError("Invalid project version.")
    if not contents["setup.bat"].isascii() or not contents["setup-runtime.bat"].isascii():
        raise ValueError("Windows CMD launcher/runtime must be ASCII.")
    if not contents["scripts/setup-ui.ps1"].startswith(b"\xef\xbb\xbf"):
        raise ValueError("PowerShell Japanese UI requires UTF-8 BOM.")
    job = json.loads(contents["jobs/us_sector_morning.json"])
    if job.get("enabled") is not False:
        raise ValueError("Unsupported US sector job must stay disabled.")
    public_job = json.loads(contents["jobs/public_sample_screen_daily.json"])
    if (public_job.get("enabled") is not False or
            public_job.get("output", {}).get("watchlistSync") is not False):
        raise ValueError("Initial public job cannot schedule or write a watchlist.")
    for path, data in contents.items():
        check_text(path, data)
        if not path.endswith(".md"):
            continue
        for match in MD_LINK.finditer(data.decode("utf-8-sig")):
            if not markdown_link_target_exists(path, match.group(2), set(contents)):
                raise ValueError(f"Broken relative Markdown link rejected: {path}")
    return version


def build_snapshot(repo: Path, output: Path, ref: str = "HEAD") -> tuple[int, str]:
    repo = repo.resolve()
    output = output.absolute()
    if output.exists():
        raise ValueError("Output already exists; refusing to overwrite.")
    if output == repo or repo in output.parents and ".git" in output.parts:
        raise ValueError("Output cannot overwrite Git metadata.")
    blobs = source_blobs(repo, ref)
    contents: dict[str, bytes] = {}
    for path, oid in sorted(blobs.items()):
        raw = git(repo, "cat-file", "blob", oid)
        if raw.startswith(b"version https://git-lfs.github.com/spec/v1"):
            raise ValueError(f"Git LFS pointer rejected: {path}")
        contents[path] = raw
    included = set(contents) | GENERATED_PATHS | {MANIFEST_PATH}
    for path in list(contents):
        if path.startswith("docs/user/") and path.endswith(".md"):
            contents[path] = clean_markdown(path, contents[path], included)
    version = tomllib.loads(contents["pyproject.toml"].decode())["project"]["version"]
    contents["README.md"] = make_readme(version)
    contents["docs/README.md"] = make_docs_index()
    # The existing PowerShell UI points at this historical manual path.
    contents["docs/WINDOWS_SETUP.md"] = (
        b"# Windows Setup\\n\\n[Current Japanese guide](user/WINDOWS_SETUP.md)\\n"
    ).replace(b"\\\\n", b"\\n")
    contents[".gitignore"] = b"runtime/\n.local/\nresults/\ndist/\n.env\n.env.*\n*.pem\n*.key\n__pycache__/\n*.egg-info/\n"
    validated_version = validate_snapshot(contents)
    digest = [
        {"path": p, "sha256": hashlib.sha256(data).hexdigest()}
        for p, data in sorted(contents.items())
    ]
    manifest = {"format": 1, "version": validated_version, "files": digest}
    contents[MANIFEST_PATH] = (json.dumps(
        manifest, indent=2, sort_keys=True, ensure_ascii=False
    ) + "\n").encode("utf-8")

    output.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=".public-snapshot-", dir=output.parent))
    try:
        for path, data in sorted(contents.items()):
            dest = temp / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        # The output contains no .git or copied Git history. A new public repo
        # is a separate owner decision, NOT performed by this tool.
        temp.rename(output)
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    return len(contents), validated_version


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--ref", default="HEAD", help="Existing local commit or ref")
    parser.add_argument("--out", type=Path, help="Fresh output directory; never overwritten")
    args = parser.parse_args()
    try:
        version = tomllib.loads(git(args.repo.resolve(), "show", f"{args.ref}:pyproject.toml").decode())[
            "project"
        ]["version"]
        out = args.out or args.repo.resolve() / "dist" / f"public-source-{version}"
        count, actual = build_snapshot(args.repo, out, args.ref)
    except (ValueError, OSError, KeyError, tomllib.TOMLDecodeError) as error:
        parser.exit(1, f"NO-GO: {error}\n")
    print(f"STAGED_ONLY: {count} files, version={actual}, path={out}")
    print("NOT PUBLISHED. Copyright, privacy and full candidate review still required.")


if __name__ == "__main__":
    main()
