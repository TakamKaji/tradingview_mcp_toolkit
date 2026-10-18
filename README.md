# tradingview_mcp_support

TradingView公式MCPを、AIアプリから共通CLI経由で扱うための軽量Pythonバックエンドです。

現在はPhase 8までの設定モデル・JSON検証・共通通信制御・MCP接続基盤・全35 Toolの型付きPython API、Screening実行・結果保存・管理Watchlist差分同期、共通Job RunnerとWindows Task Scheduler連携を実装しています。Phase 9の全米株集計はProvider coverage未確定のため保留中です。Windowsではプロジェクト内のEmbedded Pythonを使い、システムPythonを要求しません。macOSなどでは通常Pythonから手動CLIを利用できますが、SchedulerはWindowsのみです。

## 開発方針

- TradingView公式MCP `https://mcp.tradingview.com/mcp` を利用する。
- 非公式TradingView API、スクレイピング、Desktop自動操作を本線にしない。
- AIモデル差を減らすため、取得・条件判定・保存はPython側で決定論的に行う。
- 依存は最小限にし、標準ライブラリで十分な機能には追加パッケージを導入しない。
- WindowsではEmbedded Python、macOSでは通常のPython + venvを想定する。
- 実装仕様は `docs/tradingview_screening_system_spec.md` を参照する。

## Windows セットアップ

1. リポジトリをcloneする。
2. 通常ユーザー権限で `setup.bat` を実行する。
3. `app.bat mcp status` で共通CLIへ到達できることを確認する。
4. 初回未認証なら `AUTH_REQUIRED` / exit 3になるため、`app.bat mcp auth` を実行する。
5. 認証後に `app.bat mcp status` と `app.bat mcp tools` を確認する。
6. 書き込みを伴わない公開サンプルは `app.bat run public_sample_screen_daily` で試す。

`setup.bat` は初回のみEmbedded Pythonを取得します。Python本体が既にある場合も、依存パッケージの更新処理は継続して実行します。exe・標準ライブラリZIP・DLL・設定の欠落や起動検査の失敗は不完全なruntimeとして検出し、対象runtimeだけを再構築します。非対話実行では `setup.bat --no-pause` を利用できます。

`mcp status` は未認証でもブラウザを開きません。初回認証だけを `mcp auth` で明示的に開始し、OAuth credentialはWindows Credential Managerへ保存します。管理者権限、恒久PATH変更、Pythonのレジストリ登録は不要です。

公開用の `public_sample_screen_daily` は `enabled=false` / `save=true` / `watchlistSync=false` です。手動runは可能ですが `schedule apply` の登録対象にならず、TradingView WatchlistへのWriteも行いません。既存の `sample_screen_daily` はWatchlist同期を行う運用サンプルなので、初回確認では使い分けてください。

詳細は [Windows Embedded Python セットアップ](docs/WINDOWS_SETUP.md) を参照してください。

`setup.bat` / `console.bat` は通常ユーザー権限で実行する前提です。管理者として実行する必要はありません。pytestの `tmp_path` はOSの `%TEMP%` ではなく、Git管理外の `.pytest-tmp/` を使用します。これにより、過去に管理者権限で作成された `%TEMP%\\pytest-of-<user>` のACLに影響されず通常ユーザーでテストできます。WindowsでDeveloper Modeが無効な場合は、実シンボリックリンク作成を必要とする検証がskipされることがあります。

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
- `filelock>=3.12.1,<5`（非thread-local lockとPython 3.12対応）
- `tzdata>=2025.2`（WindowsなどIANA timezoneデータを持たない環境の検証用）

Development:

- `pytest>=8,<10`
- `ruff>=0.9,<1`

`requirements.txt` はWindows bootstrap互換のため `-e .[dev]` を指定します。

## 設定定義（Phase 2）

公開Screeningは `screenings/sample_standard_screen.json` です。初回確認向けの安全なJobは `jobs/public_sample_screen_daily.json` で、Scheduler登録とWatchlist同期を既定で無効にしています。`jobs/sample_screen_daily.json` は同じScreeningを参照しますが、定期登録とWatchlist同期を行う運用サンプルです。全モデルで未知キーを拒否し、JobのtimezoneはIANA名を明示する必要があります。

リポジトリのルートを起点に、Pythonから次のように検証できます。

```python
from pathlib import Path

from tradingview_screening.common.errors import ConfigError
from tradingview_screening.jobs.loader import (
    load_job_by_name,
    validate_job_screening_reference,
)

try:
    job = load_job_by_name("public_sample_screen_daily", Path.cwd())
    screening = validate_job_screening_reference(job, Path.cwd())
except ConfigError as error:
    print(error.to_dict())
```

Screening単体は `screening.validators.load_screening_by_name(name, project_root)` で読み込めます。名前からの解決は英数字で始まる英数字・`_`・`-` の名前に限定し、Windows予約名、パス区切りや定義フォルダ外へのリンクを拒否します。`builtin` Jobは `task.definition` に組み込み処理名を保持し、Screening参照検証では `None` を返します。

この段階の `filters` はIssue #4の対象である `{field: [min, max]}` 形式のみを受け付けます。片側を `null` にできますが、両端 `null`、下限が上限を超える範囲、不正な数値は拒否します。Field名の実在確認と特殊フィルター値の対応は後続フェーズで扱います。

設定の読込・参照検証はローカル処理です。Screening・Watchlist同期は明示的な実行で、定期実行はschedule applyによる登録後に行われます。

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
- Read 25件のうち通常Read 24件は `retry=True`、Write 10件は `retry=False` です。`get_active_watchlist` は分類上Readですが、Provider説明上activate/createの副作用があるため安全側で `retry=False` とします。Phase 5のwrapperは全件cacheなしです。欠落Toolはその呼出しだけ `MCP_TOOL_UNAVAILABLE` になります。
- WriteはWatchlistのcreate/delete/add/remove/updateとAlertのcreate/update/delete/stop/restartです。Phase 5時点では実Write smokeは未実施でした。Phase 7では専用テストWatchlistだけで確認しています。
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

Phase 4/5時点ではJob Runner・Schedulerは後続Phaseでした。現在は以下のPhase 8経路から同じClientを再利用します。

## Screening実行と保存結果（Phase 6）

リポジトリ直下で、Windowsは `console.bat` を開いて実行します。保存済み認証が必要です。

```bat
python -m tradingview_screening screen sample_standard_screen
python -m tradingview_screening results latest
python -m tradingview_screening results latest sample_standard_screen
```

`screenings/<name>.json` を既存モデルで検証し、定義のfiltersを解釈し直さず `TradingViewClient.run_screener()` へ渡します。サンプルのWatchlist設定がenabledでも、Phase 6ではWatchlistを操作しません。

成功結果はstdoutへJSONを1つ返し、同じ結果を `results/YYYY-MM-DD/<name>_<HHMMSS>.json` へ保存します。日付と時刻はAsia/Tokyo基準です。同一秒の衝突では `_1`、`_2` と連番を追加し、既存結果を上書きしません。失敗結果は保存しません。`results/` はGit管理外です。

`results latest` は全Screening、名前指定時はそのScreeningの保存結果を日付フォルダ横断で検索します。JSON契約・ファイル名を検証し、executedAtで最新を判定します。壊れたファイルや無関係なJSONを除外し、有効結果がなければアプリerrorを返します。

stdoutは機械可読JSON、stderrは診断用です。終了コードは0=success/partial、1=実行時失敗、2=usage/定義Validation失敗、3=AUTH_REQUIREDです。詳細は [RESULTS.md](docs/RESULTS.md) を参照してください。

名前付きScreeningでは公式presetとsymbolsetも指定できます。Provider総件数と実取得行数を分け、条件が無視された応答は保存・同期前に拒否します。日本株・S&P 500・oversold_healthy・symbolsetのread-only例は[Screening Manual](docs/SCREENING_MANUAL.md)、実測範囲は[2026-10-18検証記録](docs/MCP_VERIFICATION_2026-10-18.md)を参照してください。

### TradingView公式MCP Betaの制約（2026-10-18確認）

現行の公式MCPは、条件を全省略した全米株Screening要求をProvider側で拒否します。また `run_screener` は1回最大1000行で、当時の公式Tool schemaにページング引数はありません。したがって**全米株全体の取得・セクター平均集計は本β版では提供していません**。一方、条件付きの通常Screeningは利用可能で、S&P 500を指定した503銘柄の実機取得・限定セクター集計は成功しています。全米株の成功と混同しないでください。

これは2026-10-18時点のProvider挙動であり、公式MCP Betaの更新で変更される可能性があります。利用可能な例、制限とエラーの意味は[Screening Manualの公式MCP Beta制約](docs/SCREENING_MANUAL.md#公式mcp-beta版のスクリーニング制限2026-10-18実機確認)をご覧ください。

### 保存結果の履歴・前回比較（Phase 11）

```bat
app.bat results history public_japan_value --limit 10
app.bat results compare public_japan_value
```

保存済みの成功結果だけをローカルで読み、履歴と直近2件の観測銘柄・指標値の差分をJSONで返します。新しい成功結果には実行定義のversion付きSHA-256 fingerprintを付けます。同名でも条件が違う、旧結果にfingerprintがない、比較対象が不足する場合は理由を返し、古い比較可能な結果へ飛びません。

`completeCoverage=false`の差分は取得した観測集合の増減です。銘柄が見えなくなっても条件不適合とは断定しません。履歴・比較からMCP、認証、Watchlist、Alert、Schedulerを操作せず、結果の移行・自動保存も行いません。出力と失敗理由は[Results](docs/RESULTS.md)を参照してください。

### Phase 6の実MCP確認

2026-09-26、Windows Embedded Python 3.12.8・通常ユーザー・保存credentialで、Read-onlyの `run_screener` をlimit=1で確認しました。銘柄指定の空結果と、サンプル条件の1行取得が成功し、`structured_content.success=true`、`data.rows`、`data.totalCount`、行の `symbol` と要求列の構造を実測しました。要求外の追加列は保存対象に含めません。Providerの本文や市場データ値をfixtureへ保存していません。

Unit Test後の実CLI確認も、Embedded Python 3.12.8・管理者権限なしで成功しました。

| コマンド | 実測結果 |
| --- | --- |
| `mcp status` | 認証・Tool Discovery成功、protocol `2025-11-25`、exit 0 |
| `mcp tools` | 35 Tool、期待との差分なし、exit 0 |
| `screen sample_standard_screen` | 50件要求・50件取得、success、exit 0 |
| `results latest` | 保存済みScreening結果と一致、exit 0 |
| `results latest sample_standard_screen` | 保存済みScreening結果と一致、exit 0 |

保存先は `results/2026-09-26/sample_standard_screen_085529.json` で、stdoutとファイル内容の一致も確認しました。全5コマンドのstderrは空でした。

Phase 5で観測した日本市場scannerの429は今回の実確認では発生していません。Provider業務失敗、transport/OAuth失敗、schema不整合は別に扱い、失敗全体をpartialへ変換しません。RequestGovernorはcache利用情報を返さないため、metadataの `cacheHit` は省略します。

Phase 6の仕様変更（実測responseの正規化、cacheHit省略、同秒衝突・atomic保存・latestの契約）は、2026-09-26にGoogle Drive正本へ同期済みです。

## 管理Watchlist差分同期（Phase 7）

`screening.watchlist_sync.sync_screening_watchlist()` はPhase 6の正規化済みScreening結果を入力に、アプリ管理Watchlistへ必要なadd/removeだけを行うasync Python APIです。使用例は [SCREENING_MANUAL.md](docs/SCREENING_MANUAL.md)、保存・競合・失敗時の仕様は [WATCHLIST_SYNC.md](docs/WATCHLIST_SYNC.md) を参照してください。

- ownershipは `.local/managed_watchlists.json` に保存した `watchlistId` のみ。名前一致では既存Watchlistを採用しません。
- 初回は新規createの返却IDを保存します。expectedNameは診断用です。通常同期でdelete、名前変更、active Watchlist操作はしません。
- symbolの重複を除去し、順序差だけならWriteなし。正常successの0件は管理Watchlistを空にします。failed/partial/不正symbolを含む結果はWrite前に拒否します。
- Screening単位の作成lock、Watchlist ID単位のWrite lock、短時間のmapping更新lockを `.local/watchlist_locks/` に置きます。キーはhash化し、mappingはatomic replaceします。
- Writeは既存RequestGovernor経由でretry=False/cacheなし。add/remove後はReadで実状態を確認し、確認できた操作だけを記録します。自動rollbackはしません。
- create後mapping保存失敗では作成済ID付きエラーにして停止します。自動deleteや次回の名前一致採用はしません。

2026-09-26の専用テストで、create/getは `watchlist.id`（整数）・name・symbols、add/removeは `watchlist_id`・symbolsを実測しました。成功応答にsuccess fieldはありません。実ID・テスト名・Provider全文はfixtureへコミットしていません。

**現在のProvider制約:** 削除済みIDへのgetエラーは「不存在」と「所有権/公開アクセス不能」を区別しません。一般の `MCP_TOOL_ERROR` では自動再作成せずmappingを保持して停止します。確実な不存在を識別する実応答は未確認です。

Unit Test後の実API確認はWindows Embedded Python 3.12.8・通常ユーザーで成功しました。実Screeningの1件を新規Watchlistへ同期し、保存mappingの一致、同じ入力の再同期でWrite 0回、制御した正常空Envelopeで1件removeを確認しています。Writeはすべてretry=False/cacheなしでした。テスト用としてその実行で作成したIDだけをcleanupし、`deleted=true`を確認しました。

Phase 7の仕様はGoogle Drive正本へ反映し、読み戻しで確認済みです。既存 `screen` コマンドはReadと結果保存のみで、Watchlist設定がenabledでも同期しません。Phase 8のJob Runnerから同期APIを再利用します。

## 米国セクター集計（Phase 9・Provider制約あり）

`jobs/us_sector_morning.json`はbuiltin `us_sector_daily`のdaily 07:00 JSTサンプルです。公式MCP Betaが全米株条件なし取得を拒否するため、**enabled=false**で自動Task登録されません。明示的な手動runは可能ですが、実機ではProviderエラー（exit 1・保存なし）となりました。Windows導入の整備は別PR #21で管理します。

Universeは`america / stock`全体、取得列は`sector / change`です。1 symbol = 1票のequal weightでsector別の算術平均`meanChange`と有効銘柄数`sampleSize`を返します。同率はcompetition ranking（1, 1, 3）、表示順はsector名昇順。同値重複は1票、矛盾重複はエラー、欠損は除外、不正型はエラーです。snapshotをそのまま使い、`retrievedAt`と`sessionAssumption`を残します。OHLCV再計算・休日calendar・ニュース解釈は行いません。

2026-10-18のWindows実機で本番Jobは`PROVIDER_ERROR` / exit 1、保存なしでした。一方、検証専用S&P 500では503銘柄を全件取得して、Provider分類20セクターの平均・順位・件数を独立照合しJSON保存・読み戻しに成功しました。これは**全米株の集計成功ではありません**。公式Toolは一度に最大1000行でページング未確認です。Universeを変えるfilterは追加せず、成功応答でも`returnedCount < totalCount`なら`US_SECTOR_COVERAGE_INCOMPLETE`で保存前に停止します。重複で件数不足が隠れないようunique symbol数も確認します。

成功時はJob JSONの`builtin`にsummaryを格納し、save=trueなら`results/YYYY-MM-DD/us_sector_morning_HHMMSS.json`へ保存します。save=falseでは保存せず、builtinのwatchlistSync=trueは設定エラーです。現在のblocking limitationの詳細は[Results](docs/RESULTS.md)と[実装仕様19.3](docs/tradingview_screening_system_spec.md#193-phase-9-coverage契約とprovider制約2026-09-27)を参照してください。

## Jobs / Scheduler（Phase 8）

```bat
app.bat jobs list
app.bat run public_sample_screen_daily
app.bat run sample_screen_daily
app.bat schedule apply
app.bat schedule list
app.bat schedule remove sample_screen_daily
```

共通Job RunnerがScreening→任意保存→任意Watchlist同期を同じClient sessionで実行します。`public_sample_screen_daily` は初回確認用のread-only Jobです。`sample_screen_daily` はsave/watchlistSyncともにtrueなので、runすると管理Watchlistへ実Writeします。詳細は[Schedule Manual](docs/SCHEDULE_MANUAL.md)、AIからの操作は[AI Usage](docs/AI_USAGE.md)を参照してください。

- `enabled`は登録可否。明示的な手動runはfalseでも実行できます。jobs listは不正な定義・参照が1つでもあればexit 2です。
- 同一Job全体を`.local/job_locks/<sha256(job_name)>.lock`で保護します。重複時は待機せずalready_running/exit 0、異なるJobは独立です。
- Windows PowerShell経由のTask Scheduler COMを使用。Task名は`TradingViewMcpSupport__<job_name>`。applyは作成/更新のみで、disabled・定義消失による自動削除はしません。removeだけが完全一致Taskを削除します。
- 通常ユーザーのInteractiveToken・LeastPrivilegeで動き、ユーザーのログオンが必要です。Taskから共通app.batを呼び、system PythonやJob別BATは使いません。
- dailyのAsia/Tokyoだけを登録対象にし、+09:00を明示します。他IANA/DST timezoneはunsupportedで停止し、ローカル時刻へ読み替えません。
- Schedulerは保存済みtokenとrefreshのみ。ブラウザOAuth/DCRを起動せず、認証切れはAUTH_REQUIRED/exit 3です。
- stdoutはJob JSON 1つ。partial/重複skipはexit 0、runtime failureは1、usage/configは2です。保存・同期失敗を成功へ隠しません。
- Phase 9のbuiltin集計本体は実装済みですが、条件なし全米株取得は現行公式MCP Betaが拒否するため、全米株集計は未対応です。同梱Jobはenabled=falseです。

2026-09-26〜27、通常Windowsユーザー・Embedded Python 3.12.8で実機確認しました。sample Jobは50件を保存し、新規管理Watchlistへ同期成功。専用Jobでは空白入りディレクトリのTask作成/更新、手動Task起動と06:30の日次トリガー起動、結果1件の生成を確認しました。同一Jobの重複は手動・実Taskともexit 0でskipしました。disabled/定義削除でTaskが残り、明示removeだけで削除されることも確認し、今回作成したTask 2件はcleanup済みです。sampleの管理Watchlistとownership mappingは保持しています。

最終検証は500 passed・4 skipped（すべて従来と同じsymlink作成権限制約）、ruff成功です。Phase 8仕様はGoogle Drive正本を先に更新し、Repositoryへ同期・読み戻し確認済みです。

## Windows配布と公開導線（Phase 10）

Phase 10はPhase 9のbuiltin米国セクター集計から独立して先行できます。Windowsでは `setup.bat` がEmbedded Python、pip、依存導入までを担当し、通常実行は共通 `app.bat` へ統一します。公開用の初回JobはWatchlistへ書き込まず、定期登録も自動では行いません。

2026-10-18、Windows実機の空の検証コピーで、PATHからsystem Pythonを除外し、`setup.bat --no-pause` による新規導入、正常runtimeの再利用、標準ライブラリ欠落からの復旧を確認しました。保存済みcredentialによるstatus/toolsと公開Jobの50件保存も成功しました。新規Windowsアカウントでの初回OAuthは未実施です。条件と検証範囲は[Windows Setup](docs/WINDOWS_SETUP.md)を参照してください。

## ライセンス

MIT License。
