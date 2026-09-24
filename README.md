# tradingview_mcp_support

TradingView公式MCPを、AIアプリから共通CLI経由で扱うための軽量Pythonバックエンドです。

現在はPhase 2として、Screening / Jobの設定モデルとJSON読込・検証を実装しています。Windowsではプロジェクト内のEmbedded Pythonを使い、システムPythonを要求しない構成を主対象とします。macOSなどでは通常のPython環境からも利用できる設計にします。

## 開発方針

- TradingView公式MCP `https://mcp.tradingview.com/mcp` を利用する。
- 非公式TradingView API、スクレイピング、Desktop自動操作を本線にしない。
- AIモデル差を減らすため、取得・条件判定・保存はPython側で決定論的に行う。
- 依存は最小限にし、標準ライブラリで十分な機能には追加パッケージを導入しない。
- WindowsではEmbedded Python、macOSでは通常のPython + venvを想定する。
- 実装仕様は `docs/tradingview_screening_system_spec.md` を参照する。

## Windows セットアップ

1. リポジトリをcloneする。
2. `setup.bat` を実行する。
3. 完了後、`console.bat` を開く。

`setup.bat` は初回のみEmbedded Pythonを取得します。Python本体が既にある場合も、依存パッケージの更新処理は継続して実行します。

### 開発用コマンド

`console.bat` で開いたコンソールから実行します。

```bat
python -m tradingview_screening --help
python -m pytest
python -m ruff check .
```

## macOS / 通常Python

Python 3.11〜3.13を想定します。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m tradingview_screening --help
python -m pytest
python -m ruff check .
```

## 依存関係

依存の正本は `pyproject.toml` です。

Runtime:

- `mcp>=2,<3`
- `pydantic>=2,<3`
- `aiolimiter>=1.3,<2`
- `tenacity>=9,<10`
- `cachetools>=5,<8`
- `keyring>=25,<26`
- `filelock>=3,<5`
- `tzdata>=2025.2`（WindowsなどIANA timezoneデータを持たない環境の検証用）

Development:

- `pytest>=8,<10`
- `ruff>=0.9,<1`

`requirements.txt` はWindows bootstrap互換のため `-e .[dev]` を指定します。

## 設定定義（Phase 2）

公開サンプルは `screenings/sample_standard_screen.json` と、それを参照する `jobs/sample_screen_daily.json` です。全モデルで未知キーを拒否し、JobのtimezoneはIANA名を明示する必要があります。

リポジトリのルートを起点に、Pythonから次のように検証できます。

```python
from pathlib import Path

from tradingview_screening.common.errors import ConfigError
from tradingview_screening.jobs.loader import (
    load_job_by_name,
    validate_job_screening_reference,
)

try:
    job = load_job_by_name("sample_screen_daily", Path.cwd())
    screening = validate_job_screening_reference(job, Path.cwd())
except ConfigError as error:
    print(error.to_dict())
```

Screening単体は `screening.validators.load_screening_by_name(name, project_root)` で読み込めます。名前からの解決は英数字で始まる英数字・`_`・`-` の名前に限定し、Windows予約名、パス区切りや定義フォルダ外へのリンクを拒否します。`builtin` Jobは `task.definition` に組み込み処理名を保持し、Screening参照検証では `None` を返します。

この段階の `filters` はIssue #4の対象である `{field: [min, max]}` 形式のみを受け付けます。片側を `null` にできますが、両端 `null`、下限が上限を超える範囲、不正な数値は拒否します。Field名の実在確認と特殊フィルター値の対応は後続フェーズで扱います。

設定の読込・参照検証はローカル処理です。MCP接続、Screening実行、Watchlist同期、定期実行は後続フェーズで実装します。サンプルの有効化フラグだけで外部サービスへの操作は発生しません。

## ライセンス

MIT License。
