# tradingview_mcp_support

TradingView公式MCPを、AIアプリから共通CLI経由で扱うための軽量Pythonバックエンドです。

現在はPhase 3までの設定モデル・JSON検証・共通通信制御を実装しています。Windowsではプロジェクト内のEmbedded Pythonを使い、システムPythonを要求しない構成を主対象とします。macOSなどでは通常のPython環境からも利用できる設計にします。

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

`setup.bat` / `console.bat` は通常ユーザー権限で実行する前提です。管理者として実行する必要はありません。pytestの `tmp_path` はOSの `%TEMP%` ではなく、Git管理外の `.pytest-tmp/` を使用します。これにより、過去に管理者権限で作成された `%TEMP%\\pytest-of-<user>` のACLに影響されず通常ユーザーでテストできます。WindowsでDeveloper Modeが無効な場合は、実シンボリックリンク検証1件のみskipされることがあります。

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

## 共通通信制御（Phase 3）

`tradingview_screening.common.request_governor` の `RequestGovernor` は、Provider非依存のasync callableを実行します。`RequestGovernorConfig` で設定を渡せます。

```python
from tradingview_screening.common.request_governor import RequestGovernor

async def example():
    governor = RequestGovernor()

    async def operation():
        return {"value": 42}

    return await governor.execute(operation, cache_key="example")
```

既定値は30リクエスト/分、同時実行1、試行ごとのTimeout 30秒、初回を含め最大3試行、Retry基本待機2秒、Cache TTL 60秒です。Retry待機は指数的に増加し、小さなjitterを加えます。各試行でRate Limiterを通過し、Retry待機中は同時実行枠を解放します。

Retry対象は `TimeoutError`、`ConnectionResetError`、共通の `TransientRequestError` です。Validation・引数・権限エラーや未分類エラーは再試行しません。Write呼出元は `retry=False` を指定し、`cache_key` を省略してください。

Cacheは明示したキーに対する成功結果のみをプロセス内メモリに保存します。キー省略時とTTLが0の場合は無効です。Cache hitではoperation・Rate Limiter・同時実行枠を使用しません。同じキーの並行呼出しを1回にまとめる保証はありません。

Governorは同じイベントループ内で共有します。Cacheキーは呼出元で操作・引数・結果型を区別できるように作成してください。

Phase 4でProvider側の一時的なHTTP / MCPエラーを共通markerへ変換し、この実行経路に接続します。

## ライセンス

MIT License。
