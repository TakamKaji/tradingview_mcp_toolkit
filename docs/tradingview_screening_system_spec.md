# TradingView MCP Screening Tool — Implementation Specification

更新日: 2026-09-27
状態: V1 実装仕様
主対象: Windows / Python
副対象: macOS / 通常のローカルPython
正本管理: Google Drive版を正本とし、Repository内の同名ファイルは実装用スナップショットとして同期する。仕様変更はDrive正本を先に更新する。

Phase 4〜6の契約とPhase 7の管理Watchlist同期契約（18.4〜18.7）は、2026-09-26にGoogle Drive正本へ同期済み。

---

Phase 8のJob Runner / Scheduler契約（11.5）は2026-09-27にGoogle Drive正本へ反映し、実装用スナップショットへ同期した。

Phase 9のcoverage limitationと統合契約（19.3〜19.5）は2026-09-27にDrive正本へ先行反映する。全Universe契約を縮小しない。

## 0. この仕様書の使い方

この文書は、後でCodex等のコーディングエージェントへ渡し、リポジトリを自動実装させるための**実装仕様書**である。

実装時は次を守ること。

1. 本書の「MUST」をV1必須要件として扱う。
2. 本書の「V1対象外」を勝手に追加実装しない。
3. 不明点があっても、公式MCPリファレンスと `list_tools()` で解決できるものはそこで確認する。
4. TradingView固有のMCP処理を上位ロジックへ漏らさない。
5. AIモデルにスクリーニング条件の解釈・計算を任せない。
6. Public OSSとして公開可能な状態を維持し、認証情報・ユーザー固有データ・再配布不可データをコミットしない。
7. 実装中に仕様変更が必要になった場合は、コードだけを先行変更せず仕様書とドキュメントを合わせて更新する。

### 0.1 公式MCP資料

公式TradingView MCPドキュメントのMarkdownスナップショットを、リポジトリでは次に配置する。

```text
docs/TRADINGVIEW_MCP_OFFICIAL_REFERENCE.md
```

元URL:

```text
https://www.tradingview.com/mcp/docs
```

本書はアプリ実装仕様、`TRADINGVIEW_MCP_OFFICIAL_REFERENCE.md` は公式仕様の保存版として役割を分ける。

---

# 1. 目的

TradingView公式MCPを利用し、次を提供する軽量なローカルバックエンドを作る。

- TradingView公式MCPの全公開ToolをPythonから型付きで呼び出せる。
- TradingView Screenerを利用した名前付きスクリーニングを決定論的に実行できる。
- スクリーニング結果をJSONで保存できる。
- スクリーニング結果をTradingView Watchlistへ同期できる。
- Windowsで定期実行ジョブを簡単に追加・管理できる。
- WindowsではシステムPythonを要求せず、Embedded Pythonで実行できる。
- macOSでは通常のローカルPython環境から同じコードを実行できる。
- Antigravity / Codex / Claude Code等のAIアプリから、共通CLIを操作UIとして利用できる。
- MCPのRate Limit、Retry、Cache、同時実行数をローカル側で一元管理する。

本システムは**AIエージェントそのものではない**。
AIは操作UIおよび必要時の分析役であり、定量処理はPythonバックエンドが担当する。

---

# 2. V1の設計原則

## 2.1 MUST

- 実装言語はPython。
- Windowsを主対象とする。
- macOSでも通常のPython環境から実行可能にする。
- TradingView公式MCPを利用する。
- TradingView非公式APIやスクレイピングをFallbackとして使わない。
- CLIを共通入口とする。
- Windowsでは `app.bat` を薄いランチャーとして提供する。
- macOSでは `python -m tradingview_screening ...` を直接使えるようにする。
- すべての通常結果はJSONで返す。
- 実行結果は日付別フォルダへ保存する。
- ローカルDBを使わない。
- 常設 `logs/` ディレクトリを作らない。
- 定期ジョブ定義は `jobs/*.json` に置く。
- スクリーニング定義は `screenings/*.json` に置く。
- ジョブ追加時にBATファイルを編集しない。
- TradingView公式MCPのV1時点の全公開Toolを `TradingViewClient` で網羅する。
- MCP Tool入出力はPydantic modelで境界Validationする。
- Rate Limit / Retry / concurrency / timeout / cacheは共通 `RequestGovernor` に集約する。
- 通常運用の `maxConcurrency` は1とするが、内部APIはasync対応にする。
- TradingView WatchlistのWriteは競合しないよう制御する。
- Public版コアでは移動平均、RSI、MACD等をOHLCVからローカル再計算しない。
- AIモデルに毎回MCP Tool Schemaや大量生データを渡さない。

## 2.2 SHOULD

- MCPレスポンスの生形式を上位ロジックへ漏らさず正規化する。
- 取得Columnは必要最小限に絞れるようにする。
- 利用可能Screener Fieldは動的に取得できるようにする。
- OAuth情報はOS Credential Storeへ保存する。
- 同一Jobの多重起動を防ぐ。
- Toolset差分を診断コマンドで確認できるようにする。

---

# 3. V1対象外

以下はV1では実装しない。

- 自動売買
- 発注
- TradingView Desktop自動操作
- Playwright/SeleniumによるTradingViewログイン
- Pine Script編集
- 独自チャートUI
- localhost Web API
- ローカルMCP Server化
- SQLite/PostgreSQL等のDB
- OHLCV全履歴保存
- ローカルでの標準テクニカル指標再計算
- バックテスト
- ニュースセンチメント独自分析
- 大量並列処理
- 専用Stress/Load Test機能
- TradingView以外のMCP Provider実装
- Linux/Dockerサーバー版
- Google Drive / Sheets連携
- EDINET / J-Quants / 四季報連携

上記は将来別機能または別リポジトリとして検討可能だが、V1へ混ぜない。

---

# 4. 想定利用フロー

## 4.1 AIアプリから手動実行

```text
Antigravity / Codex / Claude Code
        ↓ shell
      app.bat
        ↓
Python CLI
        ↓
Job / Screening Loader
        ↓
TradingViewClient
        ↓
RequestGovernor
        ↓
TradingView Official MCP
        ↓
JSON保存 + stdout JSON
        ↓
AIが表示、必要時のみ分析
```

AIは原則としてTradingView MCPを直接操作せず、本リポジトリのCLIを使う。

## 4.2 Windows定期実行

```text
Windows Task Scheduler
        ↓
app.bat run <job_name>
        ↓
同じPython Job Runner
        ↓
同じTradingViewClient / RequestGovernor
        ↓
JSON保存 / Watchlist同期
```

手動実行と定期実行で別実装を作らない。

---

# 5. リポジトリ構成

```text
tradingview-screening-tool/
├─ README.md
├─ LICENSE
├─ .gitignore
├─ AGENTS.md                         # 共通AI向け最小ブートストラップ
├─ app.bat                           # Windows汎用ランチャー
├─ setup.bat                         # Windows Embedded Pythonセットアップ
├─ pyproject.toml                    # Python要件・依存の正本
│
├─ jobs/                             # 定期実行定義。浅い階層で管理
│  ├─ sample_screen_daily.json
│  └─ us_sector_morning.json
│
├─ screenings/                       # スクリーニング定義。浅い階層で管理
│  └─ sample_standard_screen.json
│
├─ src/
│  └─ tradingview_screening/
│     ├─ __init__.py
│     ├─ __main__.py
│     │
│     ├─ cli/
│     │  ├─ commands.py
│     │  └─ output.py
│     │
│     ├─ integrations/
│     │  └─ tradingview/
│     │     ├─ client.py             # 全35 Toolラッパー + MCP session
│     │     └─ schemas.py            # 全35 ToolのPydantic入出力model
│     │
│     ├─ screening/
│     │  ├─ engine.py
│     │  ├─ schema.py
│     │  └─ validators.py
│     │
│     ├─ jobs/
│     │  ├─ loader.py
│     │  ├─ runner.py
│     │  └─ scheduler.py
│     │
│     └─ common/
│        ├─ request_governor.py      # Rate/Retry/Concurrency/Timeout/Cache
│        ├─ config.py
│        ├─ errors.py
│        └─ paths.py
│
├─ results/                          # Git管理外。日付別JSON
│  └─ YYYY-MM-DD/
│
├─ docs/
│  ├─ AI_USAGE.md
│  ├─ SCREENING_MANUAL.md
│  ├─ SCHEDULE_MANUAL.md
│  ├─ RESULTS.md
│  ├─ TRADINGVIEW_MCP.md
│  ├─ TRADINGVIEW_MCP_OFFICIAL_REFERENCE.md
│  └─ TROUBLESHOOTING.md
│
├─ tests/
│  ├─ test_cli.py
│  ├─ test_screening.py
│  ├─ test_validation.py
│  ├─ test_jobs.py
│  ├─ test_scheduler.py
│  ├─ test_request_governor.py
│  └─ test_tradingview_client.py
│
├─ runtime/                          # Windows Embedded Python。Git管理外
└─ .local/                           # 必要時のみローカル秘密情報。Git管理外
```

## 5.1 配置ルール

- `jobs/` と `screenings/` は原則フラットに保つ。
- 新しい通常スクリーニングを追加するとき、Pythonコード変更ではなく `screenings/*.json` 追加を第一選択とする。
- 新しい定期実行を追加するとき、BAT/Pythonコード変更ではなく `jobs/*.json` 追加を第一選択とする。
- `state/` と `logs/` は作らない。
- `.local/` はOAuth等、どうしてもローカル永続情報が必要な場合だけ利用する。

---

# 6. CLI仕様

正式なOS非依存エントリポイント:

```text
python -m tradingview_screening <subcommand> ...
```

Windowsでは `app.bat` が上記を呼ぶ。

## 6.1 必須コマンド

```text
app.bat screen <screening_name>
app.bat run <job_name>
app.bat jobs list
app.bat schedule apply
app.bat schedule list
app.bat schedule remove <job_name>
app.bat results latest [screening_name]
app.bat mcp auth
app.bat mcp status
app.bat mcp tools
```

## 6.2 `app.bat` の制約

`app.bat` は個別Job名やScreening名を一切ハードコードしない。

責務は以下だけ。

1. Embedded Pythonの存在確認
2. 必要なら利用可能なPython実体の解決
3. `python -m tradingview_screening ...` へ引数をそのまま渡す
4. Pythonプロセスの終了コードをそのまま返す

---

# 7. JSON出力契約

CLIの機械可読な正本出力はJSONのみとする。

## 7.1 共通結果Envelope

最低限次の構造を持つ。

```json
{
  "schemaVersion": 1,
  "status": "success",
  "operation": "screening",
  "name": "sample_standard_screen",
  "executedAt": "2026-09-18T15:40:12+09:00",
  "source": "tradingview_official_mcp",
  "metadata": {
    "requestedCount": 100,
    "returnedCount": 23,
    "partial": false,
    "durationMs": 1234
  },
  "results": [],
  "errors": []
}
```

`status`:

```text
success
partial
failed
```

## 7.2 エラー

```json
{
  "code": "MCP_TOOL_UNAVAILABLE",
  "message": "Required TradingView tool is unavailable",
  "tool": "run_screener",
  "retryable": false
}
```

TradingViewやSDKの巨大な生エラー本文をそのままAI向けJSONへ流さない。
必要な診断情報だけ正規化する。

## 7.3 stdout / stderr

- 正常な機械可読結果はstdoutへJSONを1つ出す。
- 人間向け診断メッセージはstderrへ出す。
- `logs/` へ常設ファイル保存しない。

## 7.4 CLI終了コード

CLIの終了コードは次で固定する。

```text
0 = success または partial
1 = 実行時のapplication/provider failure
2 = CLI usage error またはローカルValidation error
3 = 再認証が必要（AUTH_REQUIRED）
```

`partial` はJSONの `status` / `errors` で判定し、Task Schedulerから継続利用しやすいよう終了コードは0とする。
認証失効で対話的な再認証が必要な場合のみ3を返す。

---

## 7.5 Phase 6 Screening結果の確定契約

- `screen <screening_name>` は既存Screening Validation後、`market / filters / sortBy / sortOrder / limit / columns / symbolTypes` を `RunScreenerRequest.market / filters / sort_by / sort_order / limit / columns / symbol_types` へ明示変換する。filtersの値は変えず、独自operator DSLやLLM解釈を追加しない。
- `TradingViewClient.run_screener()` → `_call_tool()` → `RequestGovernor` の既存経路だけを使用する。Watchlist設定は検証しても実行しない。
- 共通Envelopeは `schemaVersion / status / operation / name / executedAt / source / metadata / results / errors` を持つ。operationは `screening`、sourceは `tradingview_official_mcp`、executedAtはAsia/Tokyoのtimezone-aware ISO 8601。
- metadataは `requestedCount / returnedCount / partial / durationMs` を持つ。定義検証前の失敗ではrequestedCountをnullとする。returnedCountは正規化後の行数。RequestGovernorはcache hit情報を返さないため、Phase 6は `cacheHit` を省略し、推測値を入れない。
- 2026-09-26に保存credentialによるRead-only確認で、`structured_content.success=true`、`data.rows`（空配列および1行のobject配列）、`data.totalCount`（整数）、行の `symbol`（文字列）と要求列を実測した。市場データ値や生response全文は証拠fixtureとして保存しない。
- Provider固有の正規化は `integrations/tradingview/` 内に置く。行から `symbol` と要求したcolumnsだけを保存し、未知の追加fieldは許容するが保存しない。欠落列や不正shapeを推測補完せず `MCP_SCHEMA_MISMATCH` とする。content本文のJSON再parseは禁止する。
- `structured_content.success=false` はProvider業務失敗としてsecret-freeなAppErrorへ変換し、MCP transport / OAuth / MCP is_errorとは区別する。生エラー本文をstdoutや結果へ出さない。
- Phase 6は不整合な行を含む応答全体をfailedとする。部分結果の安全な契約を確認できていないため、便宜上partialを生成しない。通常のlimitによる打切りをpartialにしない。
- 終了コードは0=success/partial、1=application/provider runtime failure、2=CLI usage/local Validation、3=AUTH_REQUIRED。既存mcp auth/status/toolsを維持する。

---

# 8. 結果保存

すべての保存対象結果は日付別フォルダへ置く。

```text
results/
├─ 2026-09-18/
│  ├─ sample_screen_daily_154012.json
│  └─ us_sector_morning_070002.json
└─ 2026-09-19/
   └─ sample_screen_daily_154008.json
```

## 8.1 保存規則

- タイムゾーン既定値は `Asia/Tokyo`。
- フォルダが無ければ自動作成する。
- ファイル名は `<job_or_screening_name>_<HHMMSS>.json`。
- 同一日に複数回実行しても上書きしない。
- `results latest` は日付フォルダを横断して最新結果を解決する。
- MCP生レスポンス全量は保存しない。
- 保存するのはアプリ標準JSONと再現・診断に必要なmetadataのみ。

---

## 8.2 Phase 6保存とlatest

- 保存対象はsuccess/partialのScreening共通Envelopeのみ。failed結果は保存しない。stdoutと保存結果は同じ契約と値を使用する。
- 保存先は `results/YYYY-MM-DD/<screening_name>_<HHMMSS>.json`。日付・時刻はexecutedAtをAsia/Tokyoへ変換する。
- 同一秒の衝突では `<screening_name>_<HHMMSS>_1.json`、`_2.json` と連番を付け、既存ファイルを上書きしない。
- 同一日付フォルダ内の一時ファイルへ完全なJSONを書きfsync後、hard linkで非上書きのatomic publishを行う。公開できない場合は保存エラーとし、途中のJSONを結果として残さない。
- `python -m tradingview_screening results latest [screening_name]` は日付フォルダを横断する。指定ありは指定Screening、なしは全Screeningを対象にする。
- 日付・ファイル名・Envelopeの整合性を検証し、executedAtの絶対時刻を優先、同時刻は衝突連番等で決定的に解決する。directory mtimeには依存しない。
- path traversal、外部を指すリンク、壊れたJSON、無関係なJSON、failed結果を採用しない。有効結果がない場合は明示的なアプリerrorとする。
- `results/` はGit管理外。Watchlist同期・Job Runner・Schedulerは後続Phaseに残す。

---

# 9. Screening定義

`screenings/*.json` をスクリーニング条件の正本とする。

## 9.1 原則

- TradingView標準Screener Fieldだけで構成する。
- AIが自然言語から毎回条件を再解釈しない。
- ローカルで移動平均・RSI・MACD等を再計算しない。
- 必要FieldがTradingViewに存在するか `get_screener_columns` で確認できるようにする。
- 未知キーはValidationで拒否する。

## 9.2 定義例

実際のField名は実装時に公式MCPの `get_screener_columns` で確認して確定する。
以下は構造例であり、Field名を固定仕様としない。

```json
{
  "schemaVersion": 1,
  "name": "sample_standard_screen",
  "description": "TradingView standard screener fields only",
  "market": "japan",
  "symbolTypes": ["stock"],
  "filters": {
    "price_earnings_ttm": [null, 15]
  },
  "sortBy": "change",
  "sortOrder": "desc",
  "limit": 50,
  "columns": [
    "name",
    "description",
    "close",
    "change",
    "volume",
    "market_cap_basic",
    "sector"
  ],
  "watchlist": {
    "enabled": true,
    "name": "[Auto] Sample Standard Screen"
  }
}
```

## 9.3 Pydantic Validation

Screening定義は `screening/schema.py` のPydantic modelで検証する。

- `extra="forbid"`
- `schemaVersion` 必須
- `name` 必須
- `limit` の範囲検証
- sort orderのEnum化
- 空文字拒否
- Watchlist設定整合性検証

TradingView固有のField妥当性は必要に応じてField Discovery結果と照合する。

## 9.4 Filter契約

V1では独自のoperator DSLを作らず、TradingView公式MCP `run_screener.filters` の構造をそのまま採用する。

```json
{
  "filters": {
    "price_earnings_ttm": [null, 15],
    "change": [0, null],
    "sector": "Technology"
  }
}
```

ルール:

- 通常の数値Fieldは `[min, max]` の2要素配列。`null` は片側上限/下限なし。
- `index` / `sector` / `industry` / `analyst_rating` 等の特殊キーは、公式MCP input schemaが許可する値をそのまま使う。
- `filters` のField名は `get_screener_columns` で確認する。
- アプリ側で `gt` / `gte` / `lt` 等の独自operator表現へ変換しない。
- `sortBy` / `columns` もTradingView Screener column名を使う。
- 公式MCP schemaが変更された場合は本仕様とPydantic Schemaを同時更新する。

---

# 10. Job定義

`jobs/*.json` を定期実行定義の正本とする。

## 10.1 定義例

```json
{
  "schemaVersion": 1,
  "name": "sample_screen_daily",
  "enabled": true,
  "task": {
    "type": "screening",
    "definition": "sample_standard_screen"
  },
  "schedule": {
    "type": "daily",
    "time": "15:40",
    "timezone": "Asia/Tokyo"
  },
  "output": {
    "save": true,
    "watchlistSync": true
  }
}
```

## 10.2 Job種別

V1では最低限次を許可する。

```text
screening
builtin
```

- `screening`: `screenings/<name>.json` を参照して実行する。
- `builtin`: Python側に明示実装された組み込み処理を呼ぶ。

米国セクター日次集計など、単純なScreener定義だけでは表現しにくい処理は `builtin` とする。

## 10.3 BAT非依存

新しいJobを追加する標準手順:

```text
jobs/<new_job>.json を追加
        ↓
Validation
        ↓
app.bat schedule apply
        ↓
Windows Task Schedulerへ同期
```

`app.bat` / `setup.bat` の編集は禁止。

---

# 11. Windows Task Scheduler

V1の定期実行はWindows Task Schedulerを使う。
常駐Schedulerライブラリは導入しない。

## 11.1 `schedule apply`

- `jobs/*.json` を列挙する。
- enabledなJobをValidationする。
- Windows Task Schedulerへ作成・更新する。
- リポジトリ管理対象Taskには一定Prefixを付ける。
- 定義から消えたTaskを勝手に全削除しない。管理対象PrefixとJob名で安全に照合する。

## 11.2 実行コマンド

Task Schedulerからも必ず共通CLIを呼ぶ。

```text
app.bat run <job_name>
```

## 11.3 多重実行

同一Jobの同時実行は `filelock` で防止する。

## 11.4 V1 Scheduler契約

V1で正式サポートするschedule typeは `daily` のみとする。

- Task Scheduler上の管理Task名は `TradingViewMcpSupport__<job_name>` とする。
- `schedule apply` はenabledなJobについて作成または更新する。
- Job定義が削除・disabled化されても、`schedule apply` だけでは既存Taskを自動削除しない。
- 削除は `schedule remove <job_name>` の明示操作だけで行い、管理PrefixとJob名が一致するTaskだけを対象にする。
- 同一Jobのlock取得に失敗した二重起動は処理を実行せず、JSON metadataに `skipped: true` / `reason: "already_running"` を返して終了コード0とする。
- Task Scheduler実行中に認証切れとなってもブラウザを自動起動しない。`AUTH_REQUIRED` と終了コード3で終了する。

---


## 11.5 Phase 8実装契約

- 手動 `run <job>` はenabled=falseでも実行可能。enabledはschedule applyの登録可否を制御する。実行は共通Job Runnerで行い、Screening・保存・Watchlist同期まで同一Job lockを保持する。
- `jobs list` はflatに決定順で列挙し、全JobとScreening参照・filename/internal nameを検証する。1件でも不正なら全体をfailed、終了コード2とし、黙ってskipしない。
- Phase 8ではbuiltinを拒否していた。Phase 9では明示registryのus_sector_dailyを実行・登録対象とし、未知builtinはJOB_TASK_UNAVAILABLEを維持する。coverage制約は19.3〜19.5を参照。
- Job lockは `.local/job_locks/<sha256(job_name)>.lock`。timeout=0で競合時のみalready_running/exit0。path・権限等のlock故障を競合扱いしない。
- Job Envelopeはoperation=jobとし、Screening結果・保存済みか・相対resultPath・Watchlist同期の確定結果を区別する。save/sync未指定操作を実行済みとしない。下位failedまたはstep例外はJob failed、下位partialはJob partial。正常ScreeningのみWatchlistへ渡す。エラーはsecret-freeで、AUTH_REQUIREDはexit3、configはexit2、runtimeはexit1、partialはexit0。保存失敗後のWatchlist Writeは行わない。
- Scheduler adapterは標準Windows PowerShellからTask Scheduler COMを使う。固定scriptへJSONデータを渡し、shell=Trueやlocalized text解析を使わない。Taskはルートフォルダの管理Prefixと安全なJob名の完全一致だけを操作する。
- Task principalは現在のWindowsユーザー、InteractiveToken、LeastPrivilegeとする。管理者・パスワード登録は不要だが、そのユーザーがログオンしている間だけ動く。ログオフ中の自動実行はPhase 8の対応範囲外。S4Uはネットワーク利用制約があるため使わない。
- Task actionは共通 `app.bat run <job>` を非対話で起動し、working directoryはRepository root。Embedded Pythonと通常ユーザーのCredential Managerを使う。Job別BAT、system Python、ブラウザOAuth、DCRを使用しない。
- V1のScheduler登録対応timezoneは `Asia/Tokyo` のみ。日次StartBoundaryに明示的な `+09:00` を付ける。Windows local timezoneへ読み替えず、IANA→Windows変換表も推測しない。他のIANA timezone（DST地域を含む）はSchemaで有効でもschedule applyではSCHEDULE_TIMEZONE_UNSUPPORTEDとして拒否する。手動runの制限ではない。日本のtimezone規則が将来変わる場合は対応を見直す。
- schedule applyは全定義・有効Jobの実行可否・timezoneを事前検証してから作成/更新する。同名Taskへ安全なupdateを許容し、disabled/定義消失による自動削除をしない。Task操作途中の失敗では完了済み操作を保持してfailedを返し、自動rollbackしない。
- schedule removeはJob JSONがなくても安全な名前から完全一致Taskを削除可能。不在は機械可読な結果で返す。schedule listは管理Prefix内だけを返す。Windows以外は明示unsupported。

- AUTH_REQUIREDはpartial結果でもexit3を優先する。JOB_TASK_UNAVAILABLEとScheduler unsupportedはruntime errorとしてexit1とする。
- Task起動は非表示PowerShellの薄いwrapperから共通app.batを起動し、終了コードを伝播する。launcher起動失敗もexit1であり、成功扱いしない。Repository pathの空白は許容するが、cmdで意味を持つ危険文字を含むpathは登録前に拒否する。
- WindowsのTask名は大文字小文字を区別しないため、caseだけ異なる既存名との衝突はapply/removeとも拒否する。不在以外のCOM異常を不存在として扱わない。

- Microsoft参照: [StartBoundary](https://learn.microsoft.com/en-us/windows/win32/taskschd/trigger-startboundary)、[RegisterTaskDefinition](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskfolder-registertaskdefinition)、[WorkingDirectory](https://learn.microsoft.com/en-us/windows/win32/taskschd/execaction-workingdirectory)。


# 12. TradingView MCP Integration

TradingView固有処理は次の2ファイルを中心に閉じ込める。

```text
integrations/tradingview/
├─ client.py
└─ schemas.py
```

将来別MCPを追加する場合も同じ構造を横に追加できるようにする。

```text
integrations/
├─ tradingview/
│  ├─ client.py
│  └─ schemas.py
└─ future_provider/
   ├─ client.py
   └─ schemas.py
```

共通Rate/Retry処理はProviderごとに複製しない。

---

# 13. `TradingViewClient` 設計

## 13.1 責務

`client.py` の `TradingViewClient` は次を担当する。

- MCP Streamable HTTP接続
- OAuth session lifecycle
- `list_tools()`
- `call_tool()`
- 公式Tool名と1:1の公開asyncメソッド
- Request model → MCP arguments変換
- MCP structured content → Response model変換
- Tool存在確認
- `_call_tool()` による共通呼び出し
- Write系Toolの競合制御

## 13.2 禁止事項

- Screening EngineからMCP SDKを直接呼ばない。
- Job Runnerから `call_tool()` を直接呼ばない。
- ToolごとにRate Limit/Retryを重複実装しない。
- MCP生レスポンスを上位レイヤーへそのまま返さない。

## 13.3 公開メソッド

公式Tool名とメソッド名を一致させる。

```python
await client.run_screener(request)
await client.get_symbol_data(request)
await client.get_financials(request)
await client.create_watchlist(request)
```

全公開メソッドはasyncとする。

---

# 14. Pydantic Schema設計

`integrations/tradingview/schemas.py` にTradingView公式MCP Tool用modelをまとめる。

## 14.1 Request model

各ToolにRequest modelを用意する。

方針:

- `extra="forbid"`
- 必須/任意引数を型で表現
- Enum化可能な値はEnum化
- 範囲制約が公式仕様にある場合はValidationする
- MCPへ送信する前にValidationを完了する

Phase 5では2026-09-25の実35 `inputSchema` を正本とする。必須とnull許可は独立した契約であり、requiredかつnullableな配列もある。省略可能・非nullableのfieldへ明示的なnullを送信しない。Providerが閉じているobjectは閉じ、`run_screener.filters` 等の `additionalProperties: true` はJSON値を保持する。Phase 2のScreening定義の独自制約をMCP Requestへ持ち込まない。Alertの `patternProperties` も互換性確認対象とする。

説明文に明記された最大件数・文字数・値の列挙は根拠を明示して検証する。例示や省略記号のある一覧を閉じたenumに変えない。JSON Schemaのtitle/default等の差は無視し、property・required・型・array/object・nullability・additionalProperties・patternProperties・enum・制約を比較するテストを用意する。fixtureは取得日・protocol/server versionと35 inputSchemaだけを保存し、認証情報・Tool結果全文は含めない。

例:

```python
class GetWatchlistRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    watchlist_id: str
```

## 14.2 Response model

各ToolにResponse modelまたは正規化Response modelを用意する。

パブリックベータでレスポンスField追加があり得るため、Requestより寛容にする。

原則:

- アプリが利用する既知Fieldは型付けする。
- 将来Field追加で壊れないよう、必要なResponseでは `extra="allow"` を許容する。
- 公式レスポンスが十分確認できていないToolは、共通の最小typed envelopeでJSON値を安全に保持する。必要なfieldを型付けするときは実測のshapeを根拠とし、市場データ全文の保存を前提にしない。
- 生レスポンス全文の永続保存はしない。

35 wrapperすべてがPydantic検証済みのResponseを返す。同一契約は共通modelを共有してよく、35個の個別Response classは必須ではない。`structured_content` と `content` は分離し、content内の文章をJSONとして解釈し直さない。raw SDK `CallToolResult` は公開しない。既知fieldのValidationErrorは `MCP_SCHEMA_MISMATCH` に変換する。

2026-09-26のRead smokeで共通の `success: bool` と任意の `error` / `count` / `missing_count` を実測した8件には `ObservedReadResponse` / `ObservedReadData` を使う。残り27件は `TypedToolResponse`。Tool固有payloadはopenなJSON値として保持し、追加fieldを許容する。`success=false` のProvider業務エラーも検証済み応答として保持し、MCPの `is_error` やtransport失敗と混同しない。

## 14.3 共通model

将来、実測で必要性とfield契約が確認できた場合に次の共通化を検討する。Phase 5では未確認fieldを推測して実装しない。

```text
ToolError
ResultMetadata
PaginationInfo
SymbolRef
```

---

# 15. RequestGovernor

`common/request_governor.py` をMCP Provider共通の通信制御クラスとする。

## 15.1 責務

- Rate Limit
- 最大同時実行数
- Retry
- Exponential Backoff
- Timeout
- TTL Cache
- Retry attemptごとのRate Limit再適用

Provider固有Tool名やSchemaは持たない。

## 15.2 基本構造

```text
TradingViewClient method
      ↓
_call_tool()
      ↓
RequestGovernor.execute()
      ↓
Cache確認
      ↓
Retry attempt
      ↓
Rate Limit待機
      ↓
Concurrency slot取得
      ↓
MCP call_tool
      ↓
Result / Error normalization
```

## 15.3 既定値

既定値はコードへ散在させず設定から読む。

初期設定例:

```json
{
  "requestsPerMinute": 30,
  "maxConcurrency": 1,
  "timeoutSeconds": 30,
  "retryMaxAttempts": 3,
  "retryBaseDelaySeconds": 2,
  "cacheTtlSeconds": 60
}
```

TradingView公式MCPの公称制限は約100 tool calls/分/ユーザーだが、V1既定値は余裕を持たせる。

## 15.4 並列化

内部設計は最初からasync対応にする。

- `TradingViewClient` 公開メソッド: async
- `_call_tool()`: async
- `RequestGovernor.execute()`: async
- `asyncio.Semaphore` 等でConcurrencyを管理
- `aiolimiter` でRate Limitを管理

V1の通常設定は `maxConcurrency=1`。
将来2以上へ変更してもRate LimitとRetryが共通制御される設計にする。

## 15.5 Retry契約

Read ToolのRetry対象:

- HTTP 429
- 一時的な5xx
- Timeout
- Connection reset
- 一時的なMCP transport error

Retryしない:

- Pydantic Validation error
- OAuth権限不足 / `AUTH_REQUIRED`
- Tool not found
- 明確なargument error
- permission error

`retryMaxAttempts=3` は初回を含む最大試行回数とする。2回目・3回目の前に概ね2秒、4秒の指数Backoffへ小さなjitterを加える。
各Retry attemptは必ずRate Limiterを再通過する。

Write Toolは重複副作用を避けるためV1では自動Retryしない。429等で呼び出し前に待機することは許可するが、一度送信したWriteを自動再送しない。

---

# 16. Cache

Cacheは永続DBにしない。
原則プロセス内TTL Cacheとする。

Cache対象:

- Tool一覧
- Screener Field一覧
- Symbol検索結果
- 同一プロセス内の完全一致リクエスト

価格等の鮮度が重要なレスポンスは長時間Cacheしない。

---

# 17. OAuth / 認証情報

TradingView公式MCP:

```text
https://mcp.tradingview.com/mcp
OAuth 2.1
```

## 17.1 実装方式

OAuthプロトコルを独自実装しない。MCP Python SDKのOAuth client/providerを第一選択とし、Authorization Server discovery、PKCE、token取得・refresh等はSDKへ委譲する。

### Phase 4で確認した現行API（2026-09-25）

TradingView公式docsとインストール済みMCP Python SDK 2.2.0を確認した。接続先、Streamable HTTP、OAuth 2.1、公開Tool 35件の構成は保存版と一致する。実アカウントの利用可否と実Tool schemaは別途smoke testで確認する。

- `mcp auth` はMCPセッションから独立したOAuth bootstrapを実行する。`mcp.Client.__aenter__()` や未認証initializeの成功を前提にしない。
- bootstrapはHTTP challenge、PRM/AS discovery・検証、client登録方式選択、SDKのPKCE・ブラウザ認可・callback検証・token交換、Credential Store保存を担当する。SDKの公開 `OAuthClientProvider.async_auth_flow()` とmetadata helperを使用し、privateメソッドを呼ばない。token保存後は元HTTP要求の再送を待たず終了し、MCP/SSE接続を開始しない。
- `TradingViewClient` は保存済みcredentialを要求し、MCP接続・list_tools・call_tool・Governor連携を担当する。対話login UIを持たない。
- MCPセッションは `Client(mode="auto", cache=None)` とする。未認証の実server/discoverとinitializeはいずれも401であり、legacy固定を正当化する実証は得られていない。認証後のmodern/fallbackはSDKに委譲し、実サービスのnegotiation結果はsmoke待ち。
- 非対話OAuth refreshには `mcp.client.auth.OAuthClientProvider` と `httpx2.AsyncClient` を使い、`mcp.client.streamable_http.streamable_http_client(endpoint, http_client=...)` をClientへ渡す。status/toolsからDCR・ブラウザ認可へ移行せず、再認証が必要なら `AUTH_REQUIRED` とする。
- `TokenStorage` は `get_tokens` / `set_tokens` と `get_client_info` / `set_client_info` の4メソッドを実装する。
- callbackはtupleではなく `AuthorizationCodeResult(code=..., state=..., iss=...)` を返す。state・issはSDKへ未加工で渡す。
- `Client.list_tools(cursor=...)` の `next_cursor` を最後まで辿る。SDKの重複Cacheは `Client(..., cache=None)` で無効にし、アプリ側の共通通信制御を利用する。
- `CallToolResult.is_error` を検査し、コード向けデータは `structured_content` として扱う。`content` 本文を構造化データへ推測変換しない。
- SDK 2.2.0のHTTP層は `httpx2` を使用する。Provider内で直接importする場合は `pyproject.toml` の直接依存へ追加する。
- SDKが生成するOAuth用Requestにもアプリ固有の `User-Agent` を補完する。AsyncClientの既定headerだけではauth flow内部のRequestへ継承されない。metadata・登録・token・refreshのすべてに同じHTTP境界を適用する。
- SDK 2.2.0は保存トークンの期限と認証サーバーmetadataを再起動時に自動復元しない。取得時の絶対期限と、SDKでdiscovery・検証済みのOAuth metadataをCredential Storeに保持する。期限切れのaccess tokenは送信させず、SDKの公開 `context.oauth_metadata` を復元してSDK自身のrefresh経路へ渡す。privateな初期化・refreshメソッドは呼ばない。
- OAuth callbackは対話認証時だけ `http://127.0.0.1:8765/oauth/callback` を使用する。固定portの衝突は明示エラーとし、登録済みredirect URIを黙って変更しない。
- SDK 2.2.0のStreamable HTTP層ではHTTPステータスの詳細が一般的なMCPエラーへ変換される。Providerの公開HTTP境界で一時通信失敗・認証・権限・引数エラーを区別し、SDKセッションを壊さず共通Governorへ伝える。OAuth通信の401等は先にSDKの認証フローへ処理させる。

参照: [TradingView公式MCP](https://www.tradingview.com/mcp/docs)、[SDK Client](https://py.sdk.modelcontextprotocol.io/client/)、[SDK OAuth](https://py.sdk.modelcontextprotocol.io/client/oauth-clients/)。

### Client registrationと検証境界

- 正規の事前登録client情報がある場合はそれを優先する。なければCIMD広告と本アプリ用HTTPS metadata URLが揃う場合にCIMDを使用し、それ以外は広告された `registration_endpoint` でDCRを行う。いずれも利用できなければ `MCP_OAUTH_CLIENT_REGISTRATION_UNAVAILABLE` とする。
- 本アプリ用の公開CIMD URL・事前登録IDは現時点で存在しない。OpenAI/ChatGPTのID・CIMD URL・tokenを流用せず、外部hostingを自動作成しない。
- 公開識別子の任意設定は `TRADINGVIEW_MCP_CLIENT_ID`（正規に発行されたpublic client ID）、`TRADINGVIEW_MCP_CLIENT_METADATA_URL`（本アプリ自身のHTTPS CIMD）。token/client secretを環境変数で供給・保存しない。既存client登録の再利用はissuerと選択方式に整合する場合に限る。
- DCRは `client_name`、loopback `redirect_uris`、`grant_types=[authorization_code, refresh_token]`、`response_types=[code]`、`token_endpoint_auth_method=none`、`application_type=native` を送る。広告のない `/register` を推測しない。
- PRM resource、AS issuer、HTTPS endpointと送信先を検証する。metadata取得失敗をDCR fallbackへ進めない。PKCE・state・iss検証はSDKに委譲する。単一TradingView ASのcallbackを使用し、任意ASへcredentialを送らない。
- discovery、登録手段なし、DCR、認可、token交換、Credential Storeの失敗を固定文言の個別エラーに分類する。provider本文・token・code・state・PKCE verifierをJSON・通常ログに出さない。

### 実サーバー調査（2026-09-25）

- path付きPRMは200、root PRMは404。resourceは `https://mcp.tradingview.com/mcp`、AS issuerは `https://www.tradingview.com`。
- ASは `/mcp/oauth/authorize`、`/mcp/oauth/token`、`/mcp/oauth/register` を広告。token auth methodsは `none / client_secret_basic / client_secret_post`、PKCEは `S256`。CIMDとauthorization-response issの広告fieldはない。
- User-Agent無しのSDK metadata Requestは403。同一Requestに自アプリUser-Agentを加えると200。実SDKでMCP GET401 → PRM200 → AS200 → 正規DCR201 → redirect handler到達を確認。未補完時はAS403 → SDK推測 `/register` 404 → OAuthRegistrationErrorだった。
- 旧HTTP境界がOAuthRegistrationErrorを汎用MCP_CONNECTION_ERRORへ再変換していたため、MCP modeの変更だけでは原因を識別できなかった。
- その後、Windows Embedded Python 3.12.8・通常ユーザーで認可・callback・token交換・Credential Manager保存・MCP接続・35 Tool Discoveryまで成功。Phase 5開始時にも保存credentialでstatus / SDK list_tools成功を再確認した。protocolVersion `2025-11-25`、server `mcp-streamable-http 1.30.0`。

## 17.2 保存

認証情報はGitへ保存しない。

- Windows: `keyring` 経由でWindows Credential Managerへ保存。
- macOS: `keyring` 経由でKeychainへ保存。
- access token / refresh token / OAuth client registration情報等のsecretは平文ファイルへfallbackしない。
- Credential Storeを利用できない場合はV1では明示エラーとし、安全でない自動fallbackを行わない。
- `.local/` はlock、cache、管理Watchlist mapping等の非secretアプリ固有情報に利用してよい。

## 17.3 CLI / lifecycle

```text
app.bat mcp auth
app.bat mcp status
```

- `mcp auth` は独立OAuth loginを実行し、既定ブラウザによる認可とcredential保存を完了する。成功JSONの `authenticated: true` はOAuth完了を示し、MCP Tool discovery成功とは区別する。
- access token期限切れ時、refresh可能ならSDK経由で自動refreshする。
- refresh不能・revoked・Credential不足の場合は `AUTH_REQUIRED` を返す。
- 手動CLIの認証コマンド以外、特にTask Scheduler実行中は再認証ブラウザを自動起動しない。
- `mcp status` はendpoint到達、Credential有無、認証可否、Tool一覧取得可否をJSONで返す。

---

# 18. TradingView Watchlist同期

スクリーニング結果は必要に応じてTradingView Watchlistへ同期する。

## 18.1 標準方式

- Screening定義ごとに管理Watchlistを1つ持つ。
- 日付ごとのWatchlistを毎日新規作成しない。
- 履歴はローカルJSONに残す。
- TradingView側Watchlistは最新状態を表す。

## 18.2 差分同期

```text
現在Watchlist取得
      ↓
今回結果symbolsと比較
      ↓
追加symbols
削除symbols
      ↓
add_to_watchlist / remove_from_watchlist
```

同一Watchlistに対するWriteは直列化する。

## 18.3 管理Watchlistの所有判定

Watchlist名だけで所有判定しない。アプリが `create_watchlist` で取得した `watchlist_id` をローカルmappingへ保存し、それだけを自動同期対象とする。

保存先:

```text
.local/managed_watchlists.json
```

構造例:

```json
{
  "schemaVersion": 1,
  "screenings": {
    "sample_standard_screen": {
      "watchlistId": "12345678",
      "expectedName": "[Auto] Sample Standard Screen"
    }
  }
}
```

ルール:

- mappingが無い場合、既存Watchlistを名前一致だけで採用しない。必要なら新規作成して返却IDを記録する。
- mappingされたIDの不存在を確実に識別できた場合だけ、新規作成してmappingを更新する。現在の曖昧なProvider応答は18.5のとおり停止する。
- `expectedName` は診断用であり所有権判定には使用しない。
- ユーザー既存Watchlistへ推測でWriteしない。
- `delete_watchlist` は通常同期フローで使わない。
- mappingはsecretではないがGit管理外とする。

---

## 18.4 Phase 7 Python APIと入力

- `screening.watchlist_sync.sync_screening_watchlist(screening, normalized_result, client, project_root, *, lock_timeout=10)` を後続の呼出元から再利用する。Phase 7ではWatchlist CLIを追加せず、既存 `screen` はReadと結果保存だけを行う。Job Runner / SchedulerはPhase 8へ残す。
- watchlist未指定またはenabled=falseでは副作用なしでsuccessとskippedを返す。enabled=true/name必須の既存Validationを維持する。
- 入力はPhase 6の正規化済みsuccess Envelope。name・schemaVersion・metadata/results件数等を検証し、failed / partial / errors付き結果はWrite前に拒否する。
- `results[*].symbol` は非空のEXCHANGE:TICKER文字列で、空白・欠落・不正型等が1件でもあれば全体を拒否する。文字列を変換せず、重複を除去しsortして安定化する。
- 正常successの0件だけは空集合として扱い、管理IDの全銘柄をremove対象にする。Provider失敗を空結果として同期しない。

## 18.5 Provider正規化と不存在の境界

- 2026-09-26に専用テストWatchlistだけでcreate/get/add/removeとcleanupを実測した。create/getは `structured_content.watchlist.id` が整数、`name` が文字列、`symbols` が文字列配列。add/removeは `watchlist_id` が文字列、`symbols` が配列。成功応答にsuccess fieldは存在しなかった。
- IDはcreateが返した整数を10進文字列として保存する。IDを生成・推測しない。未知の追加fieldは許容し、上位へ渡すのはID/name/symbols等の必要最小限のみ。contentのJSON再parseは禁止。
- add/remove応答のsymbolsが全状態か操作対象かを推測せず、IDとshapeを検証した後にgetで実状態を確認する。Write後Readが失敗・不整合なら完了扱いにしない。
- 削除済みテストIDへのgetは `is_error=true`、structured_contentなしだった。エラーメッセージは不存在と所有権/公開アクセス不能を区別しない。したがって一般の `MCP_TOOL_ERROR` を不存在扱いせず、mappingを保持して停止する。
- 再作成はintegrationが確実な `WATCHLIST_NOT_FOUND` として識別できる場合だけ許可する。現Providerではその識別可能な応答は未確認であり、自動再作成の実運用経路は未確認。transport/timeout/権限/schema不整合を再作成へ流さない。

## 18.6 mappingとlock

- `.local/managed_watchlists.json` はschemaVersion=1と既定構造を厳格Validationし、未知field・空ID・不正JSONは失敗にする。expectedNameは診断用であり、現在名との一致をownership根拠にしない。
- mapping未登録なら名前検索せずcreateする。createの返却IDをmappingへ保存できてから差分Writeへ進む。通常同期ではlist_watchlists / get_active_watchlist / update_watchlist / delete_watchlistを使用しない。
- lockは `.local/watchlist_locks/` 配下。screening名とwatchlist IDをhash化して安全なファイル名にする。
- screening単位のownership lock内でmappingを再確認し、同時createを防ぐ。watchlist ID lockはget-currentから差分Write・確認Readまで保持する。
- 単一mappingファイルのread-modify-writeには短い共通lockを使用し、異なるScreeningの更新を失わないよう再読込してmergeする。リモート通信中は共通mapping lockを保持せず、異なるWatchlistは並行可能にする。
- filelockによる待機はasync呼出元を阻害せず、timeout/failureをAppErrorにする。キャンセル時も後から取得したlockを放置しない。
- mappingは同一ディレクトリのtempへwrite/flush/fsync後にatomic replaceする。symlink/junction/path escapeを拒否し、`.local/` 外へ書かない。mappingとlockは非secretのGit管理外データ。

## 18.7 差分・failure recovery・結果

- to_add = desired-current、to_remove = current-desired、unchanged = desired∩current。安定したsort順で必要差分だけを送る。順序差/完全一致ならWriteしない。
- create/add/removeは既存typed wrapper → _call_tool → RequestGovernorのみを使い、retry=False/cacheなしを維持する。独自通信Limiter/Retryを追加しない。
- add後とremove後にgetで状態を確認する。add完了確認後にremoveが失敗した場合はpartialとし、確定したaddedだけを報告する。timeout等で不明な操作はadded/removedに計上しない。
- Writeの自動再送・自動rollback・delete/recreateによる同期は禁止。
- create成功後のmapping保存失敗は明示的なmapping保存エラーと作成済IDを返す。Provider側を自動deleteせず、続くadd/removeも行わない。次回も同名Watchlistを自動採用しない。
- 同期結果はschemaVersion/status/operation=watchlist_sync/screening/watchlistId/watchlistName/created/added/removed/unchangedCount/errorsを持つ。無効設定によるskipはsuccessとskippedで表現する。
- 同期差分Write前の既知の失敗はAppErrorとして伝播する。差分Write中の失敗はfailed/partialの結果に正規化する。生Provider本文やraw SDK objectを結果へ含めない。
- 実Writeテストの削除cleanupは、その実行で新規作成した専用テストIDに限る。通常機能へWatchlist削除を追加しない。

---

# 19. 米国セクター日次集計

V1の組み込み処理として、前営業日の米国株の値上がり・値下がりセクターを集計できるようにする。

## 19.1 出力

最低限:

```text
sector
change metric
rank
sample size
retrievedAt
```

## 19.2 集計契約

V1の基準UniverseはTradingView Screenerの次の条件とする。

```text
market = america
symbol_types = ["stock"]
```

- S&P 500等の指数構成銘柄へ限定しない。
- 時価総額加重は行わない。
- `sector` と `change` を取得し、sector/changeが欠損した行は集計対象外とする。
- sectorごとに各symbolの `change` (%) の算術平均を計算する。1銘柄=1票とする。
- 平均change降順でrankを付ける。
- `sampleSize` に有効銘柄数を記録する。
- Jobは米国regular session終了後に実行する前提とする。TradingViewが返す `change` snapshotを採用し、ローカルOHLCVから前日騰落率を再計算しない。
- 実行時刻がregular session終了前の場合でも値を改変せず、metadataに実行時刻と `sessionAssumption` を残す。
- 使用Fieldは `get_screener_columns` で存在確認し、存在しないFieldを推測で代替しない。
- 「なぜ上昇したか」等のニュース解釈はこのbuiltinへ入れない。

---

## 19.3 Phase 9 coverage契約とProvider制約（2026-09-27）

- Universeは引き続き `america / stock` 全体とする。先頭1000件、S&P 500、NASDAQ限定等へ縮小しない。
- [公式MCP資料](https://www.tradingview.com/mcp/docs)と実 `list_tools/inputSchema` は `run_screener.limit` 上限1000を示し、offset/page/cursorを公開していない。filterやsymbolsetは部分集合指定であり、全Universeを重複・欠落なく列挙できる正式なpartition契約は確認できていない。未確認引数や大量分割queryを追加しない。
- 通常Windowsユーザー + Embedded Python 3.12.8のread-only実測では、MCP status成功、server 1.30.0 / protocol 2025-11-25 / 35 tools。列discoveryは `get_screener_columns(market="stock", search="sector")` と `search="change"` で成功し、両列のmarketsにstockを確認した。discoveryのmarketはstockでありamericaではない。
- `run_screener(market="america", symbol_types=["stock"], columns=["sector","change"], limit=1)` は `structured_content.success=false` でdataなし。空filtersを明示した場合、およびsortをchange/descへ明示した場合も、少なくとも1つのfilterを要求するProvider業務失敗だった。Universeを変えるfilterや、欠損銘柄を失う可能性がある見かけ上の無制限filterは追加しない。
- 条件なしamerica/stockの全Universeに対する実row shape・totalCount・全件coverageは未検証であり、実Universe件数が1000超であると実測したわけではない。一方、2026-10-18のS&P 500限定取得では `structured_content.data.rows / data.totalCount / row.symbol` とsector/changeを実応答で確認した。限定Universeの成功と全米株coverageを区別する。
- Phase 9のbuiltin / Job / 保存 / Scheduler統合コードと限定Universeでの実機保存は確認済みだが、全米株の全Universe取得と本番JSON保存は **blocking limitation** として未達を記録する。Provider契約の改善または別途承認された仕様変更があるまで本番の集計成功は保証しない。Windows導入のPhase 10とは独立して判定する。
- 成功応答ではrows数からreturnedCountを算出し、非負整数のtotalCountと比較する。returnedCount > totalCountやbool等は `MCP_SCHEMA_MISMATCH`、returnedCount < totalCountは `US_SECTOR_COVERAGE_INCOMPLETE`。完全coverage確認を通過してから集計・保存する。重複symbolによって未取得銘柄を隠さないよう、unique symbol数でも完全性を確認する。
- Provider業務失敗・coverage不足はJob failed / exit1とし、結果ファイルを生成しない。AUTH_REQUIREDはexit3、configはexit2。Provider生本文、raw response、content本文のJSON再parseは禁止する。
- 2026-10-18に `app.bat run us_sector_morning` を実機試行し、Provider拒否・exit1・保存なしを確認した。検証専用S&P 500では503銘柄を全件取得し、20分類の集計・保存・読み戻しに成功したが、全米株full coverageを意味しない。Task Scheduler実登録・Write Tool操作はPhase 9 smokeに含めない。

## 19.4 決定論集計と欠損・重複

- `meanChange` はsector別の算術平均、`sampleSize` は有効なunique symbol数。1 symbol = 1票のequal weight。時価総額加重・OHLCV再計算・ニュース解釈をしない。
- 入力順序によらない有限の平均を計算する。表示用丸めで同率を作らず、計算済みmeanChangeの数値完全一致を同率とする。competition ranking（1, 1, 3）を採用し、同率はsector名昇順。
- 同一symbolでsector/changeが一致する重複は1票。値が矛盾する重複は `MCP_SCHEMA_MISMATCH`。sectorは前後空白を除いた値、changeは検証した数値で比較する。欠損した側を保持し、残った値の矛盾も検出する。
- sector/changeの不在またはnullは除外対象。ただし片方が欠損でも、存在する他方の型は検証する。空sector、bool、NaN、Inf、不正型・row構造破損・不正symbolは `MCP_SCHEMA_MISMATCH`。
- `excludedRowCount` は欠損で除外したunique symbol数。同一欠損行の重複を二重計上しない。`validSymbolCount` は有効unique symbol数、`sectorCount` は結果sector数。
- summary EnvelopeはschemaVersion/status/operation=us_sector_summary/name=us_sector_daily/retrievedAt/source/metadata/results/errors。metadataにmarket=america、symbolTypes=["stock"]、changeMetric=tradingview_change_snapshot_percent、validSymbolCount、excludedRowCount、sectorCount、sessionAssumptionを残す。
- 米国regular session終了後に実行する運用前提をsessionAssumptionに記録する。snapshotを改変せずretrievedAtを残し、休日・早期終了calendarや前日終値の再計算を追加しない。

## 19.5 Builtin Job・保存・Scheduler

- 明示registryで `us_sector_daily` をdispatchする。未知builtinは `JOB_TASK_UNAVAILABLE`。Phase 8のScreening経路を維持する。
- 同一Job lock内で、同じTradingViewClient sessionを使ってfield discovery → Screener → 正規化 → coverage検証 → 集計 → 必要なら保存する。typed wrapper → _call_tool → RequestGovernorの経路を維持し、30 rpm / concurrency 1と既存read retryを使う。
- Job Envelopeの `builtin` に標準summaryを格納する。Screening専用fieldへ流用せず、raw responseを格納しない。
- `output.save=true` は標準summaryを `results/YYYY-MM-DD/<job_name>_<HHMMSS>.json` へ保存する。日付・時刻はretrievedAtのAsia/Tokyo表現。Screening専用Validationを流用せず、小さな共通writerでdate folder / 同秒suffix / no overwrite / atomic publish / finite JSON / path safetyを維持する。Job側resultPathは相対パス。
- `output.save=false` は取得・集計のみ行い、metadata.saved=false / resultPath=null。失敗結果は保存しない。
- builtinの `output.watchlistSync=true` は `CONFIG_VALIDATION_ERROR`。sector名をsymbolとして同期しない。
- `jobs/us_sector_morning.json` は現行Betaではenabled=false、builtin=us_sector_daily、daily 07:00 / Asia/Tokyo、save=true、watchlistSync=falseのサンプル。全米株の条件なし要求を公式Providerが拒否するため、失敗が確認済みのTaskを初期状態で自動登録しない。明示手動runは可能だがProvider制約がある。時刻は運用例であり、市場calendar判定を意味しない。
- enabledなus_sector_dailyはschedule applyの事前検証を通る。未知builtinは従来どおり拒否し、Scheduler adapter自体を変更しない。登録対応とProviderによる集計成功は別であり、上記blocking limitationは残る。
- `results latest` の既存Screening契約は変更しない。builtin保存はJobのresultPathから参照する。

# 20. TradingView公式MCP 全35 Toolラッパー

V1実装時点で、公式ドキュメントに掲載されている全35 Toolを型付き公開メソッドとして実装する。

公開Pythonメソッド名は本仕様表の論理名（例: `run_screener`, `list_watchlists`）を維持する。一方、2026-09-25の実 `list_tools()` ではTradingView系が `mcp-tv-*`、Watchlist系が `mcp-watchlist-*` のwire名で公開されている。実MCP呼出し・Tool availability判定・差分検知は `integrations/tradingview/tool_catalog.py` の論理名→wire名mappingを唯一の変換点として使用し、論理名をそのまま `call_tool()` へ送らない。

実装着手時に次を必ず行う。

1. `docs/TRADINGVIEW_MCP_OFFICIAL_REFERENCE.md` を確認。
2. `list_tools()` の実レスポンスを確認可能なら照合。
3. Tool名・input schemaに差分がある場合は現行公式側へ合わせる。
4. 仕様書のTool表も更新する。

## 20.1 Watchlists — 8

| Tool | 種別 | 機能 | 主な引数 |
|---|---|---|---|
| `list_watchlists` | Read | Watchlist一覧取得 | なし |
| `get_watchlist` | Read | Watchlistと構成銘柄取得 | `watchlist_id` 必須 |
| `get_active_watchlist` | Read | アクティブWatchlist取得 | なし |
| `create_watchlist` | Write | Watchlist新規作成 | `name?`, `symbols?` |
| `delete_watchlist` | Write | Watchlist削除 | `watchlist_id` 必須 |
| `add_to_watchlist` | Write | 銘柄追加 | `watchlist_id`, `symbols` 必須 |
| `remove_from_watchlist` | Write | 銘柄削除 | `watchlist_id`, `symbols` 必須 |
| `update_watchlist` | Write | 名前・説明更新 | `watchlist_id` 必須, `name?`, `description?` |

## 20.2 Market data — 3

| Tool | 種別 | 機能 | 主な引数 |
|---|---|---|---|
| `get_ohlcv` | Read | OHLCVバー取得 | `symbol` 必須, `interval?`, `count?`, `summary?` |
| `get_economic_data` | Read | 経済指標時系列 | `symbol` 必須, `date_from?`, `date_to?` |
| `get_economic_symbols` | Read | 経済指標Ticker検索 | `country?`, `category?`, `search?` |

`get_ohlcv.interval` 現行候補:

```text
1m / 5m / 15m / 30m / 1h / 4h / 1D / 1W / M / 1mo / month
```

`count` は現行最大5000本。

## 20.3 Symbol search — 1

| Tool | 種別 | 機能 | 主な引数 |
|---|---|---|---|
| `search_symbols` | Read | Ticker/名称からTradingView Symbol検索 | `query` 必須, `type_filter?` |

現行 `type_filter` 候補:

```text
stock / etf / bond / forex / index / futures / crypto / all
```

## 20.4 Screener — 5

| Tool | 種別 | 機能 | 主な引数 |
|---|---|---|---|
| `get_symbol_data` | Read | 1銘柄のScreener列取得 | `symbol` 必須, `columns?` |
| `run_screener` | Read | Screener実行 | `market?`, `filters?`, `sort_by?`, `sort_order?`, `limit?`, `columns?`, `symbol_types?`, `filter_preset?`, `symbolset?` |
| `get_symbol_data_batch` | Read | 最大50銘柄まとめて列取得 | `symbols` 必須, `columns?` |
| `get_screener_columns` | Read | 利用可能列/時間足Variant検索 | `market?`, `group?`, `search?` |
| `get_technicals_rating` | Read | 最新テクニカルスナップショット | `symbol` 必須, `interval?` |

`run_screener` はV1の中心Tool。
現行 `limit` 最大1000件。
`get_technicals_rating.interval` 現行候補:

```text
1m / 5m / 15m / 30m / 1h / 2h / 4h / 1D / 1W / 1M
```

## 20.5 News — 2

| Tool | 種別 | 機能 | 主な引数 |
|---|---|---|---|
| `get_news` | Read | 銘柄ニュース一覧 | `symbol` 必須, `lang?`, `limit?`, `offset?` |
| `get_news_story` | Read | News IDから本文取得 | `id` 必須, `lang?`, `user_prostatus?`, `user_country?` |

## 20.6 Fundamentals & forecasts — 3

| Tool | 種別 | 機能 | 主な引数 |
|---|---|---|---|
| `get_forecasts` | Read | アナリスト予想等 | `symbol` 必須 |
| `get_financials` | Read | 財務指標スナップショット | `symbol` 必須, `metric?`, `period?` |
| `get_financial_history` | Read | 財務指標履歴 | `symbol` 必須, `period?`, `date_from?`, `date_to?` |

現行period候補:

```text
get_financials: fy / fq / ttm / fh / current
get_financial_history: fq / fy
```

## 20.7 Documents — 2

| Tool | 種別 | 機能 | 主な引数 |
|---|---|---|---|
| `get_documents` | Read | 決算資料・開示・Transcript等一覧 | `symbol` 必須, `category?`, `event?`, `start_date?`, `end_date?`, `limit?` |
| `get_document_view` | Read | `view_id` から本文取得 | `view_id` 必須 |

`view_id` は `get_documents` の返却値を利用し、ローカルで組み立てない。

## 20.8 Calendars — 3

| Tool | 種別 | 機能 | 主な引数 |
|---|---|---|---|
| `get_earnings_calendar` | Read | 決算予定・実績 | `symbols` 必須, `date_from?`, `date_to?` |
| `get_economic_calendar` | Read | 経済イベント | `countries?`, `currencies?`, `category?`, `date_from?`, `date_to?`, `min_importance?` |
| `get_dividends_calendar` | Read | 配当・権利落ち等 | `symbols?`, `market?`, `date_from?`, `date_to?`, `limit?` |

## 20.9 Alerts — 8

| Tool | 種別 | 機能 | 主な引数 |
|---|---|---|---|
| `create_alert` | Write | 価格Alert作成 | `symbol` 必須, `price?`, `condition?`, `message?`, `name?`, `resolution?`, `expiration?`, 通知設定等 |
| `update_alert` | Write | Alert設定変更 | `alert_id` 必須, `message?`, `name?`, `expiration?`, 通知設定等 |
| `delete_alert` | Write | Alert削除 | `alert_ids` 必須 |
| `stop_alerts` | Write | Alert停止 | `alert_ids` 必須 |
| `restart_alerts` | Write | Alert再開 | `alert_ids` 必須 |
| `list_alerts` | Read | Alert一覧 | `symbol?`, `active?` |
| `get_alerts` | Read | Alert詳細 | `alert_ids` 必須 |
| `get_alerts_log` | Read | Alert発火履歴 | `days?`, `symbol?`, `limit?` |

現行 `create_alert.condition` 候補:

```text
cross / cross_up / cross_down / greater / less
```

## 20.10 Tool数

```text
Watchlists                 8
Market data                3
Symbol search              1
Screener                   5
News                       2
Fundamentals & forecasts   3
Documents                  2
Calendars                  3
Alerts                     8
-----------------------------
Total                     35
```

---

# 21. MCP Tool Discovery / 差分検知

TradingView公式MCPはPublic Betaのため、Tool追加・Schema変更を前提とする。

## 21.1 コマンド

```text
app.bat mcp tools
```

JSONで最低限次を出す。

```text
name
description
inputSchema
implemented: true/false
```

## 21.2 期待Tool差分

期待35件の**wire名**と取得一覧から `expectedMissing` / `unexpectedAvailable` を返し、各Toolに `expected` と `implemented` を付ける。Phase 5では既知35件のwrapperが実装済みであり、未知の追加Toolは `implemented: false` とする。不足Toolがあっても一覧診断自体は成功させる。公式説明上の論理名と実サーバーwire名は直接比較しない。2026-09-25の実機確認では35件すべて取得でき、論理名をそのまま期待値にした旧catalogでは35件すべてがmissing/unexpectedに誤分類されたため、以後は `TOOL_NAME_MAP` のvalueを期待wire名の正本とする。

アプリ実装済み35 Toolと `list_tools()` を比較し、次を区別する。

```text
implemented_and_available
implemented_but_missing
available_but_not_implemented
```

Public Beta中の追加Toolを発見しても、通常Jobを失敗させない。
必須Toolが欠けている場合だけ対象Jobを明確なエラーで失敗させる。

## 21.3 Beta互換性ルール

- `available_but_not_implemented` があってもアプリ起動・既存Jobを失敗させない。
- `implemented_but_missing` はそのToolを必要とする操作だけ `MCP_TOOL_UNAVAILABLE` で失敗させる。
- Tool名は存在するがinput schemaが実装時fixture/期待Schemaと互換でない場合、その操作だけ `MCP_SCHEMA_MISMATCH` で失敗させる。
- Beta差分を理由に無関係なJobを停止しない。
- `mcp tools` は差分をJSONで表示し、実装更新判断に使えるようにする。

---

# 22. Read / Write Tool方針

Read Toolはユーザー指示またはJob定義に従って実行可能。

Write Toolは次のルールを守る。

- 自動実行で標準的に利用するWriteは管理Watchlist同期のみ。
- Alertsの作成/更新/削除は明示指示がある場合のみ。
- Watchlist削除は通常同期フローで使わない。
- ユーザー既存Watchlistへ推測でWriteしない。
- Write系は同一対象に対して直列化する。

---

# 23. Python / 依存関係

## 23.1 Python互換

```text
Python >= 3.11, < 3.14
```

Windowsでは検証済みPython Embeddable Packageを `runtime/` に展開する。
macOSではユーザーの通常Python + venvを利用する。

互換性契約とWindows同梱Runtimeは分ける。

```text
アプリ互換範囲: Python >= 3.11, < 3.14
Windows bootstrap既定Runtime: Python 3.12.8
```

Windows bootstrapのpatch versionは再現性のため固定する。更新は専用変更として `setup.bat` と実機テストを同時に行う。
アプリ全体の互換範囲を3.12.8だけへ狭める意味ではない。

## 23.2 `pyproject.toml`

依存の正本は `pyproject.toml`。

```toml
[project]
requires-python = ">=3.11,<3.14"
dependencies = [
  "mcp>=2.2,<3",
  "httpx2>=2.13,<3",
  "pydantic>=2,<3",
  "aiolimiter>=1.3,<2",
  "tenacity>=9,<10",
  "cachetools>=5,<8",
  "keyring>=25,<26",
  "filelock>=3.12.1,<5",
  "tzdata>=2025.2"
]

[project.optional-dependencies]
dev = [
  "pytest>=8,<10",
  "ruff>=0.9,<1"
]
```

直接importしない推移依存を重複して明示依存にしない。

`tzdata` はWindows Embedded Python等、OS側にIANA timezone databaseが無い環境で標準ライブラリ `zoneinfo` を利用可能にするためのデータ依存として明示する。Timezone API自体は標準ライブラリ `zoneinfo` を使用し、独自timezoneライブラリは導入しない。

## 23.3 標準ライブラリ利用

次は外部依存を増やさない。

| 機能 | 標準ライブラリ |
|---|---|
| CLI | `argparse` |
| JSON | `json` |
| Path | `pathlib` |
| 日時/Timezone | `datetime`, `zoneinfo` |
| async | `asyncio` |
| subprocess | `subprocess` |
| browser起動 | `webbrowser` |
| hash | `hashlib` |
| temp | `tempfile` |

## 23.4 V1で入れない依存

```text
pandas
numpy
polars
APScheduler
schedule
typer
click
python-dotenv
requests
orjson
sqlalchemy
playwright
selenium
fastapi
flask
```

---

# 24. Windows Embedded Python

`python_embedded_tool` の思想を土台として利用するが、本プロジェクトへ必要な部分だけ取り込む。

## 24.1 `setup.bat` 責務

1. `runtime/` へ検証済みPython Embeddable Packageを展開。
2. pipを利用可能にする。
3. 本リポジトリをインストール。
4. `pyproject.toml` 依存を解決。
5. `python -m tradingview_screening --help` を実行して起動確認。

Playwright/Chromiumはインストールしない。

Python本体が既にあっても依存更新を実行できるようにする。

## 24.2 環境Invariant

- Embedded Pythonの目的はシステムPythonを要求しないことであり、Windowsユーザー環境全体を仮想化しない。
- `USERPROFILE` / `HOME` / `APPDATA` / `LOCALAPPDATA` / `TEMP` / `TMP` をプロジェクト配下へ上書きしない。
- `PYTHONHOME` / `PYTHONPATH` はプロセス内でクリアし、Embedded PythonをPATH先頭へ追加する変更もそのBATプロセス内だけとする。
- OS環境変数の恒久変更、レジストリへのPython登録、システムPythonへのpip installを行わない。
- `setup.bat` / `console.bat` / 通常CLIは管理者権限を要求しない。通常ユーザー権限での実行を標準とし、Windows Credential Managerや既定ブラウザ等もそのユーザーコンテキストを利用する。
- pytestの一時領域はOSの `%TEMP%` に依存せず、Repository直下のGit管理外 `.pytest-tmp/` を `--basetemp` で使用する。管理者実行で作られたユーザーTemp配下のpytestディレクトリACLが通常ユーザー実行を妨げないようにする。
- Windowsで実シンボリックリンク作成権限が無い場合、権限依存のテストはskipを許容する。全テストPASSのために管理者権限を要求しない。
- `pythonXY._pth` isolated modeを前提に、Windows Embedded環境のeditable installではbuild backendを先にEmbedded Pythonへ導入し `--no-build-isolation` を使う。通常Python/macOSにはこの制約を広げない。

---

# 25. macOS

macOSではEmbedded Pythonを使わない。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m tradingview_screening --help
```

ジョブ定義、Screening定義、結果形式、MCP ClientはWindowsと同一。

macOSの定期実行機構はV1の必須対象外。

---

# 26. AI向けドキュメント

## 26.1 `AGENTS.md`

詳細仕様を重複しない。
最低限次だけを記載する。

- `README.md` を読む。
- `docs/AI_USAGE.md` を読む。
- 通常操作は共通CLIを使う。
- TradingViewへ独自に直接アクセスするコードを追加しない。
- 新規Screeningはまず `screenings/*.json` 追加で実現する。
- 新規定期実行はまず `jobs/*.json` 追加で実現する。
- V1対象外機能を勝手に追加しない。

## 26.2 `docs/AI_USAGE.md`

- AIアプリでリポジトリを開いた後の利用方法
- 代表CLI
- 結果JSONの読み方
- 分析は結果取得後にAI側で行うこと
- MCPを直接AIコンテキストへ展開しすぎないこと

## 26.3 `docs/SCREENING_MANUAL.md`

- Screening定義Schema
- 利用可能Fieldの確認方法
- 新規定義追加手順
- Validation方法
- Watchlist同期設定

## 26.4 `docs/SCHEDULE_MANUAL.md`

- Job定義Schema
- `schedule apply/list/remove`
- Task Schedulerとの関係
- 多重実行時の挙動

## 26.5 `docs/TRADINGVIEW_MCP.md`

本プロジェクトでのMCP利用方法を説明する。
公式全文は別の `TRADINGVIEW_MCP_OFFICIAL_REFERENCE.md` を参照する。

---

# 27. テスト方針

Stress Test専用機能は作らない。
通常テストで重要境界を確認する。

## 27.1 必須Unit Test

- Screening JSON Validation
- Job JSON Validation
- Result JSON生成
- 日付別保存
- `results latest`
- Rate Limit呼び出し経路
- Retry対象/非対象判定
- Cache hit/miss
- maxConcurrency=1の直列化
- File lockによる同一Job多重起動防止
- Watchlist差分計算
- MCPエラー正規化

## 27.2 TradingViewClient Test

- 35公開メソッドが存在する。
- 35メソッドが共通 `_call_tool()` を経由する。
- Request modelから正しいTool argumentへ変換される。
- mocked structured responseをResponse modelへ変換できる。
- Write Toolの自動再送・cacheが無効であり、共通Governorのconcurrency/timeoutを通る。対象別Lockは後続Watchlist同期Phaseの検証対象。
- Tool unavailableを明確なアプリErrorへ変換する。

## 27.3 Integration Test

実アカウントを必要とするテストは通常CIから分離する。

ローカル明示実行で確認する項目:

- OAuth
- `list_tools()`
- `run_screener`
- `get_screener_columns`
- Watchlist作成/追加/削除/更新
- その他35 Toolの最低限smoke call（安全に実行できるRead Tool中心）

Write Toolの破壊的テストは、明示許可された専用テスト用Watchlist/Alertだけを対象にする。Phase 5では実Writeを実行しない。Read smokeはREADMEの8件を対象とする。

---

# 28. Public OSS制約

- OAuth tokenをコミットしない。
- API Key/Cookie/Session情報をコミットしない。
- `runtime/`, `.local/`, `results/` を `.gitignore` する。
- TradingView取得データの大量サンプルをリポジトリへ含めない。
- サンプル結果はダミーまたは再配布可能な最小データにする。
- READMEでTradingView公式MCPを利用することを明示する。
- 非公式TradingView APIを利用していると誤認されない説明にする。

Public版の価値は、TradingView公式MCPをAI会話へ直接丸投げするのではなく、**決定論的なPython CLI / JSON / Rate Limit / Job定義 / Watchlist同期の層で包むこと**にある。

---

# 29. 参考実装

以下は設計参考として読むが、コードやデータ経路をそのまま採用する前提ではない。

```text
https://github.com/fiale-plus/tradingview-mcp-server
https://github.com/atilaahmettaner/tradingview-mcp
```

参考観点:

- MCP + CLIの共通ロジック
- JSON出力
- 定義ファイル
- Schema Version
- Validation
- Rate Limit
- Retry / Backoff
- TTL Cache
- Partial Success
- Metadata
- async対応

非公式TradingView endpoint、スクレイピング、独自売買シグナル等は採用しない。

---

# 30. 実装順序

Codex等に実装させる場合は原則この順番で進める。

## Phase 1 — Repository foundation

1. `pyproject.toml`
2. `src/tradingview_screening/` package
3. `__main__.py`
4. CLI骨格
5. path/config/error utilities
6. `.gitignore`
7. README/AGENTS骨格

### 完了条件

```text
python -m tradingview_screening --help
```

がWindows/macOSの通常Python環境で動く。

## Phase 2 — Config models

1. Screening Pydantic model
2. Job Pydantic model
3. JSON loader
4. Validation error JSON
5. sample定義

### 完了条件

- 正常定義を読み込める。
- 未知キーや不正値を拒否できる。

## Phase 3 — RequestGovernor

1. Rate Limit
2. concurrency
3. Retry
4. timeout
5. TTL Cache
6. Unit Test

### 完了条件

mock処理で直列・Retry・Cacheがテストできる。

## Phase 4 — TradingView MCP foundation

1. MCP接続
2. OAuth
3. `list_tools()`
4. `_call_tool()`
5. Tool差分検知
6. `mcp auth/status/tools`

### 完了条件

実アカウント環境でTool一覧取得まで成功する。

## Phase 5 — 全35 Tool schema / wrappers

1. `schemas.py`
2. 35 Request models
3. 全35 wrapperでPydantic Response/normalized modelを使用（共通model可）
4. 35 async public methods
5. Unit tests

### 完了条件

- 全35メソッドが存在。
- 全メソッドが共通 `_call_tool()` / `RequestGovernor` 経由。
- 公式Tool一覧との照合テストがある。
- `TOOL_NAME_MAP` を唯一の論理名→wire名変換に使う。Request/public wrapper/policy coverageは35件、mappingのkey/valueはいずれも一意。
- Read 25件のうち通常Read 24件は `retry=True`。`get_active_watchlist` は分類上Readだが、Provider説明上activate/createの副作用があるため `retry=False` とする。Write 10件（Watchlist create/delete/add/remove/update、Alert create/update/delete/stop/restart）は `retry=False, cache_key=None`。全wrapperでcacheを使用しない。
- 必須・任意・nullable・未知field・境界値と、全35 wrapperの呼出経路・再試行policyをtable driven testで検証する。
- 実35 inputSchema snapshotとの互換性と、破壊的drift・追加/欠落Toolを検出するテストがある。
- Unit Test後にReadのみ実アカウントsmokeを行う。`get_active_watchlist` はProvider説明上activate/createの副作用があり対象外とする。Writeはmockで検証し、実応答shapeは未確認と明記する。
- AlertのWebhook作成とWebhook付きAlert更新はMCP非対応。`update_alert` はcondition/symbol/timeframe変更不可。回避操作を実装しない。
- Screening engine・結果保存・Watchlist同期・Job Runnerは実装しない。

## Phase 6 — Screening

1. Screener definition → `run_screener`
2. result normalization
3. JSON stdout
4. date folder保存
5. `results latest`

### 完了条件

名前付きScreeningを1コマンドで実行しJSON保存できる。

## Phase 7 — Watchlist sync

1. 管理Watchlist解決
2. 現在symbols取得
3. 差分計算
4. add/remove
5. Write lock

### 完了条件

Screening結果とTradingView Watchlistが同期する。

## Phase 8 — Jobs / Scheduler

1. Job Runner
2. `run <job>`
3. Windows Task Scheduler adapter
4. `schedule apply/list/remove`
5. 多重実行lock

### 完了条件

Job JSONを追加するだけでBAT編集なしに定期Taskへ反映できる。

## Phase 9 — Built-in US sector summary

1. 必要Screener Field確認
2. deterministic aggregation
3. JSON result
4. Job sample

### 完了条件

前営業日の米国セクター上昇/下落順位をJSONで保存できる。

2026-09-27時点では19.3のProvider制約により、全Universe取得とlive保存の完了条件は未達。安全な統合実装とUnit Testを先行し、blocking limitationとして追跡する。

## Phase 10 — Windows Embedded setup / Docs

1. `setup.bat`
2. `app.bat`
3. `README.md`
4. docs一式
5. Public sample

### 完了条件

Python未インストールWindows環境で、`setup.bat` → `app.bat mcp status` まで到達できる。

---

# 31. V1受け入れ条件

以下をすべて満たしたらV1実装完了とする。

## 31.1 Runtime / portability

- [ ] WindowsでシステムPythonを要求せずセットアップできる。
- [ ] macOSの通常Python + venvで起動できる。
- [ ] Python 3.11〜3.13範囲の少なくともCI対象バージョンでUnit Testが通る。

## 31.2 CLI

- [ ] `screen`
- [ ] `run`
- [ ] `jobs list`
- [ ] `schedule apply/list/remove`
- [ ] `results latest`
- [ ] `mcp auth/status/tools`
- [ ] success/partialはexit 0、usage/validationは2、AUTH_REQUIREDは3の終了コード契約を満たす。

が実装されている。

## 31.3 MCP

- [ ] TradingView公式endpointへ接続できる。
- [ ] OAuth認証できる。
- [ ] `list_tools()` できる。
- [ ] 35 Toolすべてに型付きラッパーがある。
- [ ] 35 ToolすべてにPydantic Request modelがある。
- [ ] Responseを正規化できる。
- [ ] Tool差分を検知できる。
- [ ] Tool追加では無関係Jobを失敗させず、missing/schema mismatchは対象操作だけを正規化エラーにする。
- [ ] OAuth secretはkeyringへ保存し、Task Schedulerから対話認証を起動しない。

## 31.4 Request control

- [ ] Rate Limitが共通化されている。
- [ ] Retryが共通化されている。
- [ ] Timeoutが共通化されている。
- [ ] TTL Cacheが共通化されている。
- [ ] `maxConcurrency=1` で直列動作する。
- [ ] 設定変更で将来Concurrencyを増やせる構造になっている。

## 31.5 Screening / result

- [ ] `screenings/*.json` の追加だけで標準Screeningを増やせる。
- [ ] Screening filtersは公式MCP `{field: [min,max]}` 契約を使用し、独自operator DSLを持たない。
- [ ] Screening条件をAIが再解釈しない。
- [ ] 結果はJSON。
- [ ] 結果は `results/YYYY-MM-DD/` へ保存。
- [ ] 同一日再実行で上書きしない。
- [ ] `results latest` で最新結果を取得できる。

## 31.6 Watchlist

- [ ] Screening定義からWatchlist同期を有効化できる。
- [ ] 追加・削除差分同期できる。
- [ ] ユーザー既存Watchlistを勝手に変更しない。
- [ ] `.local/managed_watchlists.json` の保存済みwatchlist_idだけを自動同期対象とする。
- [ ] 同一WatchlistのWrite競合を防止できる。

## 31.7 Scheduling

- [ ] `jobs/*.json` の追加だけでJobを増やせる。
- [ ] `app.bat` をJobごとに編集しない。
- [ ] `schedule apply` でTask Schedulerへ同期できる。
- [ ] 手動実行と定期実行が同じJob Runnerを通る。
- [ ] V1 schedule typeはdaily、Task名Prefixは `TradingViewMcpSupport__`、削除は明示removeのみ。

## 31.8 Quality

- [ ] `pytest` PASS
- [ ] `ruff` PASS
- [ ] 認証情報がGit対象外
- [ ] `runtime/`, `.local/`, `results/` がGit対象外
- [ ] READMEから最短利用手順が分かる
- [ ] `docs/TRADINGVIEW_MCP_OFFICIAL_REFERENCE.md` が含まれる

---

# 32. Codex実装時の禁止事項

Codex等の実装エージェントは以下を行わないこと。

- V1対象外機能の先回り実装
- TradingView非公式API利用
- Playwright/Selenium追加
- pandas/numpy追加
- DB追加
- FastAPI/Flask追加
- 独自GUI追加
- MCP Server自作
- 独自OAuthプロトコル実装
- JobごとのBAT作成
- ScreeningごとのPythonスクリプト作成
- ローカル技術指標計算の標準機能化
- 大量生MCPレスポンスの保存
- OAuth tokenの平文コミット
- 35 Toolの一部を「今使わないから」という理由で省略

---

# 33. 参照資料

公式TradingView MCP:

```text
https://www.tradingview.com/mcp/docs
https://mcp.tradingview.com/mcp
```

リポジトリ内保存版:

```text
docs/TRADINGVIEW_MCP_OFFICIAL_REFERENCE.md
```

MCP Python SDK:

```text
https://py.sdk.modelcontextprotocol.io/
```

参考OSS:

```text
https://github.com/fiale-plus/tradingview-mcp-server
https://github.com/atilaahmettaner/tradingview-mcp
```

Windows Embedded Python土台参考:

```text
https://github.com/TakamKaji/python_embedded_tool
```

---

# 34. Codex開発オーケストレーション

本リポジトリのCodex開発では役割を分離する。

```text
Root / Orchestrator: GPT-6 Astra (high)
Implementation subagent: GPT-6 Sol (high)
```

## 34.1 Astraの責務

- 本仕様と現行コードの確認
- タスク分解とAcceptance Criteria定義
- 実装対象をSolへ委任
- 複数実装の競合回避
- 実装結果のアーキテクチャレビュー
- pytest / ruff /必要な統合確認結果の最終判定
- 仕様変更が必要な場合の明示

Astraは `src/` / `tests/` の本実装を原則自分で書かず、GPT-6 Sol implementerへ委任する。小さな説明文・設定・仕様整理はAstraが直接変更してよい。multi-agent機能が利用不能な場合は、Solへ委任できないことを明示し、ユーザー許可なしにAstra単独実装へ切り替えない。

## 34.2 Sol implementerの責務

- 指定された狭い実装範囲のコード調査
- Python実装
- 必要なUnit Test追加・修正
- `pytest` / `ruff` 実行
- 変更ファイル、テスト結果、残課題をAstraへ返す
- 依頼外の大規模リファクタを行わない

## 34.3 Codex設定

プロジェクト `.codex/config.toml` ではRootをAstraにし、spawnされるsubagentの既定モデルをSolへ設定する。

```toml
model = "gpt-6-astra"
model_reasoning_effort = "high"
model_verbosity = "low"

[agents]
enabled = true
default_subagent_model = "gpt-6-sol"
default_subagent_reasoning_effort = "high"
```

同一ファイルを複数subagentへ同時編集させない。短い依存タスクは無理に分割せず、実装担当Sol 1つを基本とする。

---

# 35. 将来拡張の境界

V1完了後、必要性が確認された場合のみ追加検討する。

- 別MCP Provider
- Linux/Docker無人運用版
- Drive / Sheets
- EDINET / J-Quants
- 決算資料自動整理
- ユーザー個人用テクニカル計算
- Read系MCP Callの並列化
- 複数プロセス共通Rate Limiter
- Web UI

追加時も、原則として以下の拡張規則を守る。

```text
MCP Provider追加:
  integrations/<provider>/client.py
  integrations/<provider>/schemas.py
  既存 RequestGovernor を再利用

Screening追加:
  screenings/*.json を優先

Job追加:
  jobs/*.json を優先

独自処理追加:
  必要性が定義ファイルでは表現できない場合だけPythonコードを追加
```

---

# 36. Screening selector・件数契約の拡張（2026-10-18 / Issue #22）

## 36.1 定義とProviderへの写像

schemaVersion=1を維持し、既存filtersの数値[min,max]とindex/sector/industry/analyst_rating文字列の形式を維持する。任意filterPresetを既存wrapperと同じ6 preset（pullback_with_reversal / breakout_with_volume / oversold_healthy / earnings_runup / relative_strength / new_highs）に限定し、filter_presetへ渡す。任意symbolsetは空でない文字列配列としてそのまま渡す。独自filter DSLは設けない。

両selectorを省略した既存定義はそのまま利用できる。空filtersの定義は互換性のため許容するが、条件をすべて省略した要求がProviderに拒否された場合は業務失敗として伝播する。

## 36.2 条件が無視された応答

structured_content.success=trueだけで成功を確定しない。data.ignored_filtersが存在するとき、空配列だけを許容する。非空または型不正ならMCP_SCHEMA_MISMATCHとして停止し、raw Provider本文を出さない。失敗は0件成功やpartialへ読み替えず、保存・Watchlist同期を実行しない。

実測ではdividends_yield_ttmがcolumnsのカタログに存在してもfilterとして無視された。日本株公開例は公式alias pe=[0,15] / div_yield=[3,null]を用い、予想配当利回り条件であることを明示する。

## 36.3 成功結果の件数

既存metadata.requestedCount（定義limit）とreturnedCountを保持し、成功時にrequestedLimit / totalCount / limitReached / completeCoverageを一組で追加する。

- requestedLimit: 定義limit、requestedCountと一致。
- totalCount: Provider data.totalCountの非負整数。実返却行数以上。
- limitReached: returnedCount >= requestedLimit。
- completeCoverage: returnedCountと一意symbol数の両方がtotalCountに一致。

totalCount=503 / returnedCount=5 / requestedLimit=5ならlimitReached=true、completeCoverage=false。totalCountとlimitが同じで全行揃えば両flagがtrueになる。これは要求された条件内の件数整合であり、市場全体や別Universeの完全性は保証しない。limit到達だけではpartialにしない。

旧4項目を持たない保存結果は引き続き読み込む。追加4項目の一部欠落、型不正、件数・flagの矛盾は保存/latest/Watchlist入力で拒否する。既存の上位N件Watchlist同期はcompleteCoverage=falseでも可能とする。

## 36.4 公開例・検証範囲

日本株条件、S&P 500 filter、oversold_healthy、S&P 500 symbolsetの各公開定義はlimit=5 / watchlist.enabled=false。対応Jobはenabled=false / save=true / watchlistSync=falseとし、Scheduler登録を自動実行しない。

2026-10-18、既存Python TradingViewClientで35 ToolをDiscoveryし、Screenerのschemaは従来と同じ、上限1000、pagination/offset/cursorなしと確認した。日本株1037件中5件、S&P 500とsymbolsetは503件中5件、presetは115件中5件を取得した（件数は観測値）。

stockカタログの17グループ/163カラムも観測値であり、固定件数をテスト要件にしない。EMA50/EMA200と乖離率はpreset実応答で確認したProvider計算値を使う。PublicコアでOHLCVから計算しない。

条件なしamerica/stockは依然Providerが拒否した。全米株Universeの完全取得手段は未確認で、19.3〜19.5のPhase 9 blocking limitationを解除しない。S&P 500や先頭1000件への縮小、未確認pagination/filter分割は行わない。

---

# 37. 保存Screeningの履歴・前回差分（Phase 11 / Issue #24）

## 37.1 実行定義fingerprint

新しい成功Screening結果のmetadata.definitionFingerprintへ {version:1, algorithm:"sha256", value:<64桁の小文字hex>} を追加する。schemaVersion=1と旧保存結果の読取を維持する。

hash対象は検証済み定義のmarket、symbolTypes、filters、filterPreset、symbolset、sortBy、sortOrder、limit、columnsの9項目。全項目をモデル既定値込みで取り出し、JSONのsort_keys=True、separators=(",", ":")、ensure_ascii=False、allow_nan=Falseでcanonical化し、UTF-8のSHA-256とする。objectキー順を正規化し、配列順は保持する。

name、description、watchlist設定、実行時刻、結果値は対象外。同名でも条件変更やlimit/columns変更は別identityとして比較を拒否する。旧結果へ現在の定義からfingerprintを後付けしない。

## 37.2 履歴取得

results history <screening_name> [--limit N] を追加する。limit既定20、許容範囲1〜1000。ローカルの成功・検証済みsnapshotを新しい順に列挙し、0件は成功の空itemsとする。

operation=screening_historyのJSON 1個に、各snapshotのfile（プロジェクト相対POSIX）、executedAt、returnedCount、totalCount、completeCoverage、definitionFingerprintを返す。旧形式の未記録情報はnull。

日付folder/filename/executedAtの整合、有限JSON、既存結果metadataを検証する。破損JSON、危険なpath/symlink、failed/partialは履歴から除外する。絶対時刻降順、同時刻は数値serial、filenameの順で安定化し、mtimeを利用しない。名前にpath traversalを許可しない。

## 37.3 直近2件の比較

results compare <screening_name> を追加する。直近2件の成功snapshotを選択し、古いfromと新しいtoとして比較する。2件不足はNO_BASELINE等の区別可能な理由を返す。fingerprint・symbol等の比較可否は選択後に判定し、旧形式・条件不一致・未対応fingerprintや重複を飛ばして古い比較可能ペアへ置き換えない。

壊れたJSON・基本Envelope不整合・危険pathは履歴同様に比較候補から除外する。fingerprintやcoverage flagの整合・重複・指標値は選択後に検証する。比較時に現在のScreening定義を読み直したり、MCPへ問い合わせたりしない。

成功はoperation=screening_compareの独立JSON。from/toのfile・日時・fingerprint・coverage、fingerprintMatched、observedAdded、observedRemoved、observedCommon、indicatorChanges（共通銘柄の列別before/after）、totalCountChangeを返す。不正fingerprintの参照値はnullにし、不正本文をechoしない。

EXCHANGE:TICKERを変更せず比較キーにする。不正symbol、重複、型不正、非有限値を黙認しない。結果行順の変更だけで銘柄差分を作らず、symbol/列の順序を決定的にする。値の欠落とnull、boolとnumberを区別する。 指標値は有限number/string/bool/nullを扱い、複合object/arrayはINVALID_VALUESで比較不可とする。numberの1と1.0は同値。列before/afterはpresent/valueで未記録とnullを区別する。

## 37.4 Coverageと失敗の意味

両snapshotのcompleteCoverage=trueかつ同一fingerprintを確認できた場合だけfull_matched_setとする。それ以外はobserved_set_onlyであり、observedRemovedを条件不適合・失格とは断定しない。limitや順位で観測されなかった可能性を明記する。

totalCountChangeはProvider総件数の差で、取得済みsymbol数の差とは別。旧形式等で総件数不明ならnullにする。

比較不能はstatus=not_comparableと理由、CLI exit 1。履歴成功/比較成功はexit 0、引数Validationはexit 2。不正なpathやローカル読取失敗もsecret-freeなJSON errorとして返す。 reasonはNO_BASELINE / MISSING_FINGERPRINT / INVALID_FINGERPRINT / UNSUPPORTED_FINGERPRINT / DEFINITION_MISMATCH / INVALID_SYMBOLS / INVALID_VALUES / INVALID_METADATAを区別する。

## 37.5 境界と検証

履歴と比較はローカルread-only。MCP追加アクセス、OAuth/credential変更、Watchlist/Alert Write、Scheduler変更、差分自動保存、Job自動実行連携を行わない。既存ファイルの移行・削除を行わず、screen / results latest / run / jobs / schedule / Watchlist / 35 Tool / RequestGovernorを維持する。Phase 9 / Issue #18 / PR #19は変更しない。

テストは0/1/複数履歴、複数日付・同秒serial、完全/不完全coverage、同条件・filter/limit/columns変更、順序変更、列値変更、旧形式、破損JSON、不正数値・symbol・重複、symlink/path traversal、比較がMCP/外部Writeを呼ばないことを含む。

---

以上。
