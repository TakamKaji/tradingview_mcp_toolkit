# tradingview_mcp_support

TradingView公式MCPを、AIアプリから共通CLI経由で扱うための軽量Pythonバックエンドです。

現在はPhase 5までの設定モデル・JSON検証・共通通信制御・MCP接続基盤・全35 Toolの型付きPython APIを実装しています。Windowsではプロジェクト内のEmbedded Pythonを使い、システムPythonを要求しない構成を主対象とします。macOSなどでは通常のPython環境からも利用できる設計にします。

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

現行の[TradingView公式MCP docs](https://www.tradingview.com/mcp/docs)と、インストール済み **MCP Python SDK 2.2.0** の公開APIを2026-09-25に確認しました。接続はStreamable HTTP・OAuth 2.1です。`mcp auth` はMCPセッションを作らず、SDKの公開 `OAuthClientProvider.async_auth_flow()` で独立したOAuth bootstrapを実行します。`status` / `tools` は保存済みcredentialを読み、`Client(mode="auto", cache=None)` で接続します。

初回認証の順序は、HTTP認証challenge → Protected Resource Metadata → Authorization Server Metadata → client登録方式選択 → SDKのPKCE・ブラウザ認可・callback検証 → token交換・Credential Store保存です。`auth` の成功はOAuth完了を示し、MCPセッション・Tool一覧取得の確認は続く `status` / `tools` が担当します。

2026-09-25の実測ではTradingViewはDCR endpoint、public clientの `none`、PKCE `S256` を広告し、CIMD対応は広告していませんでした。本アプリ用の公開CIMD URL・事前登録IDも未設定のため、広告されたDCRを採用します。`registration_endpoint` のないサーバーに推測の `/register` を送信しません。OpenAI/ChatGPTのclient identityは使用しません。

正規のpublic client IDが別途発行された場合は `TRADINGVIEW_MCP_CLIENT_ID`、本アプリ自身のHTTPS CIMDを用意した場合は `TRADINGVIEW_MCP_CLIENT_METADATA_URL` で指定できます。いずれも通常は未設定です。これは公開client識別子の設定であり、token・client secretの環境変数保存には使用しません。CIMD URLの設定だけでは文書の所有権や公開内容の正しさは保証されないため、本アプリ管理下の文書を使用してください。

同日の障害調査では、SDK生成OAuthリクエストの `User-Agent` 欠落でAS metadataが403となり、SDKの推測DCRが404になる経路を再現しました。アプリ固有の `User-Agent` を補完するとmetadata 200 → 正規DCR 201へ進み、その後のWindows実機smokeでもブラウザ認可・token交換・Credential Manager保存・MCP接続・Tool Discoveryまで成功しました。実サーバーは protocolVersion `2025-11-25`、server version `1.30.0` を返し、35 Toolを公開していました。

TradingView公式資料で使われる論理名（例: `run_screener`, `list_watchlists`）と、実MCPサーバーが `list_tools()` で返すwire名は異なります。2026-09-25実測ではTradingView系は `mcp-tv-*`、Watchlist系は `mcp-watchlist-*` でした。Phase 5の公開Pythonメソッド名は論理名を維持し、実MCP呼出しは `tool_catalog.TOOL_NAME_MAP` でwire名へ解決します。Tool差分検知もwire名同士で比較します。

TradingView MCPの利用にはEssential以上の対象プランが必要です。trialは対象外です。利用権限不足は認証不足と区別して返します。

Unit Testは実TradingView・ブラウザ・OS Credential Storeへアクセスしません。実アカウントでの確認は、管理者として起動していない `console.bat` から次の順序で行います。

```bat
python -m tradingview_screening mcp auth
python -m tradingview_screening mcp status
python -m tradingview_screening mcp tools
```

1. 初回の `auth` で既定ブラウザが開き、TradingViewの認可を完了できることを確認します。認証済みの場合は再度開かないことがあります。
2. `status` が認証成功とTool discovery可否をJSONで返し、ブラウザを開かないことを確認します。
3. `tools` が実Tool一覧と期待35件に対する不足・追加を返し、ブラウザを開かないことを確認します。Phase 5では既知35件の `implemented` は `true`、未知の追加Toolは `false` です。
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

Python側は `async with TradingViewClient() as client` で接続し、`await client.list_tools()` で正規化した `ToolCatalog` を取得します。内部の `_call_tool(name, arguments, retry=..., cache_key=...)` は共通Governorを通り、`ToolCallData` の `structured_content` と `content` を分離して返します。

## 型付きTool API（Phase 5）

`integrations.tradingview.schemas` の35 Request modelと、`TradingViewClient` の同名asyncメソッドを利用します。Watchlists 8、Market/Economic 3、Symbol 1、Screener 5、News 2、Fundamentals 3、Documents 2、Calendars 3、Alerts 8の全35件が対象です。

```python
from tradingview_screening.integrations.tradingview.client import TradingViewClient
from tradingview_screening.integrations.tradingview.schemas import RunScreenerRequest

async def example():
    async with TradingViewClient() as client:
        result = await client.run_screener(
            RunScreenerRequest(market="japan", symbolset=["TSE:7203"], limit=50)
        )
        return result.structured_content
```

- 公開メソッドは論理名です。共通typed invocationが `TOOL_NAME_MAP` でwire名へ変換し、`_call_tool()` と既存Governorを通ります。
- Requestは2026-09-25の実35 `inputSchema` を基準に、必須・省略可能・null許可を区別します。未知キーは原則拒否し、Providerが許容するopen object / pattern propertyは維持します。`run_screener.filters` はJSON objectで、Phase 2のScreening定義の範囲検証とは別です。
- 全wrapperはPydantic検証済みResponseを返します。`structured_content` と `content` は分離し、文章を自動で構造化データとして読み替えません。未確認の応答fieldを必須化せず、Betaでの追加fieldを保持します。不正な既知fieldは `MCP_SCHEMA_MISMATCH` です。
- 実測済みRead 8件は `ObservedReadResponse` / `ObservedReadData` で `success` と、存在する場合の `error` / `count` / `missing_count` を型付けします。残り27件は `TypedToolResponse` でJSON値を保持します。Tool固有のdata/bars等の詳細構造はまだ厳格化していません。
- Read 25件は `retry=True`、Write 10件は `retry=False`。Phase 5のwrapperは全件cacheなしです。欠落Toolはその呼出しだけ `MCP_TOOL_UNAVAILABLE` になります。
- WriteはWatchlistのcreate/delete/add/remove/updateとAlertのcreate/update/delete/stop/restartです。実アカウントのWrite smokeは実施しません。
- `get_active_watchlist` は分類上Readですが、Provider説明には未選択時のactivate・Watchlist不在時の作成があるため、読み取り専用smokeから除外します。
- AlertのWebhook作成・Webhook付きAlertの更新はMCP非対応です。`update_alert` ではcondition/symbol/timeframeを変更できません。schema上の許可はProviderの操作対応を保証しません。

### schema driftと検証

実 `inputSchema` だけを取得日・protocol/server versionとともに `tests/fixtures/tradingview_input_schemas_2026-09-25.json` へ保存しています。永続的な公式仕様ではなくBetaの比較基準です。互換性テストはproperty・required・型・nullability・additionalProperties・patternProperties・enum・既知制約を比較し、title/default等を含むJSON全体一致は使いません。schemaにはなく説明文に明記された制約は、根拠となる文言とともにテスト側で管理します。

Unit Testは保存済みsnapshotを使うオフライン検証です。Provider更新の確認時は明示的に `mcp tools` を実行してsnapshotを見直します。実行時にschema全体の一致を要求して非破壊的な追加まで拒否する処理は設けません。

2026-09-26にも保存credentialで `mcp status` / `mcp tools` を再実行し、35件すべて `implemented=true`・不足0件・追加0件、その時点の実inputSchemaとRequest modelの互換性35/35を確認しました。CLI JSONはASCIIエスケープを使い、Windowsのcp932でもProvider説明文のUnicode記号で失敗しないようにしています。

実アカウントsmokeはUnit Test後、保存credentialを使って上記APIから `search_symbols`、`get_ohlcv`、`get_symbol_data`、`get_symbol_data_batch`、`get_screener_columns`、`run_screener`、`get_technicals_rating`、`get_economic_symbols` を呼びます。銘柄は `TSE:7203`、取得件数は少数に限定し、認証情報・市場データ全文をログやfixtureへ保存しません。

Providerの `structured_content.success=false` は、MCPの `is_error` とは別の業務エラー応答です。wrapperが値を返しただけでデータ取得成功とは判定せず、実測済みRead応答の `success` と、バッチ取得の欠落情報も確認してください。`run_screener` はinputSchema上全引数が省略可能ですが、2026-09-26実測では `filters` / `filter_preset` / `symbolset` のいずれかがない呼出しをProviderが拒否しました。Python側に未公表の独自必須条件は追加せず、その応答を保持します。

2026-09-26の通常Windowsユーザー・Embedded Python 3.12.8での実測結果:

| Read Tool | 結果 |
|---|---|
| `search_symbols` | `7203`検索で5件、success=true |
| `get_ohlcv` | `TSE:7203`日足3本、success=true |
| `get_screener_columns` | stockのclose検索で3列、success=true |
| `get_economic_symbols` | JPのinflation検索で22件、success=true |
| `get_symbol_data` / `run_screener` / `get_technicals_rating` | 応答型検証は成功。Provider内の日本市場scannerが429でsuccess=false |
| `get_symbol_data_batch` | 応答型検証は成功。success=trueだが0件、missing_count=1（TSE:7203のQuote未取得） |

8件とも `ObservedReadResponse` として応答を検証できましたが、実データ取得が成功したのは4件です。他の27件は実呼出し未確認であり、全35件の成功応答shapeを実機確認したという意味ではありません。

Screening実行engine・結果保存・Watchlist同期・Job Runnerは後続Phaseの対象です。仕様書のPhase 5契約はRepositoryへ先行反映しているため、Google Drive正本更新が必要です。

## ライセンス

MIT License。
