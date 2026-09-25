# tradingview_mcp_support

TradingView公式MCPを、AIアプリから共通CLI経由で扱うための軽量Pythonバックエンドです。

現在はPhase 4までの設定モデル・JSON検証・共通通信制御・MCP接続基盤を実装しています。Windowsではプロジェクト内のEmbedded Pythonを使い、システムPythonを要求しない構成を主対象とします。macOSなどでは通常のPython環境からも利用できる設計にします。

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

- `mcp>=2.2,<3`
- `httpx2>=2.13,<3`（SDKのHTTP認証・エラー分類に使用）
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

設定の読込・参照検証はローカル処理です。Screening実行、Watchlist同期、定期実行は後続フェーズで実装します。サンプルの有効化フラグだけで外部サービスへの操作は発生しません。

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

Phase 4のProvider層が一時的なHTTP / MCPエラーを共通markerへ変換し、この実行経路に接続します。

## MCP接続と実アカウントsmoke test（Phase 4）

現行の[TradingView公式MCP docs](https://www.tradingview.com/mcp/docs)と、インストール済み **MCP Python SDK 2.2.0** の公開APIを2026-09-25に確認しました。接続はStreamable HTTP・OAuth 2.1です。[SDK公式OAuth手順](https://py.sdk.modelcontextprotocol.io/client/oauth-clients/)に従い、`OAuthClientProvider` → `httpx2.AsyncClient` → `streamable_http_client` → `mcp.Client` の構成を使います。

TradingView MCPの利用にはEssential以上の対象プランが必要です。trialは対象外です。利用権限不足は認証不足と区別して返します。

Unit Testは実TradingView・ブラウザ・OS Credential Storeへアクセスしません。実アカウントでの確認は、管理者として起動していない `console.bat` から次の順序で行います。

```bat
python -m tradingview_screening mcp auth
python -m tradingview_screening mcp status
python -m tradingview_screening mcp tools
```

1. 初回の `auth` で既定ブラウザが開き、TradingViewの認可を完了できることを確認します。認証済みの場合は再度開かないことがあります。
2. `status` が認証成功とTool discovery可否をJSONで返し、ブラウザを開かないことを確認します。
3. `tools` が実Tool一覧と期待35件に対する不足・追加を返し、ブラウザを開かないことを確認します。Phase 4の `implemented` は全件 `false` です。
4. 新しい `console.bat` を開いて `mcp status` を再実行し、プロセスを跨ぐCredential永続化を確認します。
5. 期限切れ後の `status` でrefresh可能ならブラウザなしで成功すること、認可失効後は `AUTH_REQUIRED`・終了コード3になることを確認します。
6. いずれのstdout/stderrにもtoken・client secret・認可codeが出ていないことを確認します。

認証callbackは認証中だけ `http://127.0.0.1:8765/oauth/callback` で待機します。port競合は明示エラーになり、別portへ切り替えません。state・issの検証はSDKへ委譲します。

token・client registration・SDKで検証済みの認証サーバーmetadataは `keyring` 経由でWindows Credential Manager / macOS Keychainに保存します。平文ファイルへのfallbackはありません。SDK 2.2.0で再起動時に失われる期限・metadataを補完し、refresh自体はSDKに任せます。認証不足やrefresh不能時も `status` / `tools` はブラウザを開きません。

CLIの終了コードは成功0、通信・権限・Credential Store等の失敗1、usage/ローカルValidation 2、再認証要求3です。通常結果はstdoutにJSONを1個返します。

`mcp auth` 成功時の出力例:

```json
{"schemaVersion":1,"status":"success","operation":"mcp_auth","authenticated":true}
```

`mcp status` は `endpoint`、`credentialPresent`、`authenticated`、`toolDiscoveryAvailable` と取得可能な `protocolVersion` / `serverInfo` を返します。保存情報を読み取れない場合の `credentialPresent` は `null` です。Credential Storeのservice名は `tradingview-mcp-support/oauth` で、token・client_info・oauth_metadataを別entryに保持します。

Python側は `async with TradingViewClient() as client` で接続し、`await client.list_tools()` で正規化した `ToolCatalog` を取得します。内部の `_call_tool(name, arguments, retry=..., cache_key=...)` は共通Governorを通り、`ToolCallData` の `structured_content` と `content` を分離して返します。個別Tool wrapperはPhase 5で追加します。

このsmoke testで実Tool名・input schemaを確認してから、Phase 5の個別型付きwrapperへ進みます。

## ライセンス

MIT License。
