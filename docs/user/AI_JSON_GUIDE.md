# AIによるScreening生成ガイド：標準JSONと高度なPython処理

この文書は**ChatGPT・Codexなど共通の作成ガイド**です。**単一Screeningで表現できれば方式A（JSON）を必ず優先し、表現できない処理だけ方式B（Python）を選びます。** 日本語を正本とし、末尾に英語の要点を載せています。標準利用ではCodex・Git・ホストへのPython導入は必須ではありません。高度なPython処理には、ソースを編集・検証できる実行環境が必要です。

## AIが確認するファイル（この順）

1. [このガイド](AI_JSON_GUIDE.md)、[README](../../README.md)、[機能の対応範囲](FEATURES.md)
2. [Screeningの全項目・条件・制約](SCREENING_MANUAL.md)
3. Jobが必要なら[Jobの全項目・時刻・副作用](SCHEDULE_MANUAL.md)
4. 実際のサンプル：[Screening](../../screenings/public_japan_value.json)・[読み取り専用Job](../../jobs/public_sample_screen_daily.json)
5. 実際の[Screening Schema](../../src/tradingview_screening/screening/schema.py)・[Job Schema](../../src/tradingview_screening/jobs/schema.py)、[公式Providerの資料](https://www.tradingview.com/mcp/docs)・[型付きRequest](../../src/tradingview_screening/integrations/tradingview/schemas.py)

**必ず実際のファイルを読んでから作成してください。** 公開URLでもAIの閲覧機能やアクセス権によっては本文を読めません。読めないAIは閲覧したふりをせず、上記資料の添付・本文の提供を求めてください。Privateの間は通常の公開URLでは閲覧できません。新しいfilter・列・市場等はProviderの対応を確認し、Schemaが文字列を受理するだけで対応済みとしないでください。

## AIによる方式選択フロー

1. **希望を整理する。** 市場・銘柄母集団、条件、処理順、ランキングと件数、時間足・指標期間、取得列、保存、Jobの要否を確認する。PERの下限や利回りの予想/TTMなど、結果を変える曖昧さは説明・確認する。
2. **実仕様と照合する。** 上記Schema・公式Provider対応項目・同梱例で、希望を単一Screeningとして表現できるか確認する。
3. **可能なら必ず方式A。** `screenings/*.json`を生成し、Jobが求められた場合だけ`jobs/*.json`も作る。簡単な条件のたびにPython・BAT・独自実行環境を増やさない。
4. **Aで表現できない処理だけ方式B。** 「上位N件を確定してから別時間足で判定するため」など、Pythonが必要な理由を短く説明する。不明なProvider項目をPythonに変えれば使えるとは扱わない。必要データの対応を確認できなければ、その部分を未対応・未確認として止める。
5. **保存・ローカル検証・実取得・Writeを分ける。** ファイル作成だけの依頼でTradingViewへ接続しない。利用者の明示依頼なしにTradingViewへの実書き込みやScheduler登録・削除を行わない。

| 希望 | 選択 | 成果物・理由 |
| --- | --- | --- |
| 対応済みの市場・filter・sort・limit・columns、任意のsymbolset・preset | **A：標準JSON** | 単一Screeningで表現可能。Screening JSON、必要な場合だけJob JSON |
| 複数段階の抽出、ランキング確定後の別時間足判定、外部母集団との照合が必要 | **B：複合Python** | 単一JSONには段階・結合・後段判定を記述できない。Pythonと必要設定・依存・起動手順 |
| Provider対応や取得の完全性を確認できない | **制約を報告** | 条件や母集団を黙って変更しない。Pythonでも取得保証は増えない |

### 判定例（条件固有のファイルは同梱しない）

**ケースA：「日本株でPER15倍以下、配当利回り3%以上を出来高順で20件取得する」→ 方式A。** `market=japan`、`pe`・`div_yield`、`sortBy=volume`、`sortOrder=desc`、`limit=20`で表現できる。同梱例の`pe=[0,15]`は負のPERを除外し、`div_yield=[3,null]`は**予想配当利回り**を使う。PERの上限だけなら`[null,15]`との違いを説明し、利回りの基準も確認する。TTMを求められた場合、未確認のfilterへ置き換えない。Jobの希望がなければScreening JSONだけを提供する。

**ケースB：「グロース市場全体を対象に日足出来高上位100件を確定してから、1時間足RSI14が40以下の銘柄を抽出する」→ 方式B。** 「母集団を確認 → 日足出来高で順位確定 → その100件だけに1時間足RSI14の判定 → 保存」という順序が必要。現行の単一Screening JSONには段階や独立した時間足の後段判定を表す項目がない。Job JSONも単一のScreening参照でこの順序を追加できない。

最初からRSI条件を併用して取得すると、**RSI条件を満たす集合の出来高上位100件**になり、依頼と異なる。日本株の先頭1000件を取ってからグロース市場と照合しても、市場全体の上位100件とは保証できない。母集団、日足出来高、1時間足RSI14の取得方法・完全性を確認してから実装する。この2例は方式選択の説明であり、実取得の成功を示すものではない。

## 利用者が送る依頼文

> https://github.com/TakamKaji/tradingview_mcp_support の `docs/user/AI_JSON_GUIDE.md` とリンク先の実仕様・Schema・サンプルを確認してください。私の希望から、単一Screening JSONで可能なら必ずJSON方式を選び、Jobは必要な場合だけ作成してください。表現できない複合処理だけPythonを選び、理由と必要なデータ・環境を説明してください。未確認の条件やAPIは創作せず、取得制限を明示してください。完成ファイル、保存先、検証・実行手順を教えてください。今回はファイル作成とローカル検証までとし、TradingViewへの実取得・書き込みとScheduler登録は行わないでください。

Pythonを必要とする依頼例：

> ランキング確定後に別時間足で判定したいです。まず単一JSONで可能か確認し、不可なら理由を説明して複合Python処理を作成してください。既存の公式MCPクライアントと安全機構を再利用し、母集団・指標の出所・時点と段階ごとの件数を記録してください。未取得・欠損を0件成功として扱わず、実取得やWatchlist同期はまだ行わないでください。

## 方式A：JSONの作成ルール

- **正しいJSONだけをファイルへ保存。** UTF-8（BOMなし）、コメント・余計な末尾カンマ・Markdownコードフェンスなし。JSON全文を省略しない。
- 新しいファイル名は英数字で始め、続きは英数字・`_`・`-`のみ。パス・空白・日本語・Windows予約名は使用禁止。`screenings/<name>.json`や`jobs/<name>.json`の`<name>`をJSON内の`name`と一致させ、既存サンプルを上書きしない。
- Screeningの`schemaVersion`は整数`1`、`limit`は整数1～1000、`columns`は空でない配列。通常の数値`filters`は`[下限, 上限]`で、片側の制限なしは`null`。例：`"pe":[0,15]`、`"div_yield":[3,null]`。フィルター名と取得列名は異なる場合がある。
- **Providerの未確認フィルター・列・市場・presetを創作しない。** 未対応・不明な希望は利用者に伝え、勝手に別条件や別Universeへ置き換えない。`mcp tools`はツール一覧表示であり、任意Toolの実行用CLIではない。
- ScreeningのWatchlistは最初`{"enabled":false}`。Jobは`schemaVersion=1`、`task.type="screening"`、`task.definition`に**Screening名**、`enabled=false`、`output.save=true`、`output.watchlistSync=false`。Jobの`schedule`は手動実行でも必須。現行Schedulerは`daily`、`HH:MM`、`Asia/Tokyo`のみに対応。時刻の希望がなければ例示時刻を明示し、実際の定期登録をしない。
- **Watchlistへの銘柄追加・削除やTask登録・削除はユーザーの明示依頼なしに行わない。** 同梱`sample_screen_daily`は`enabled=true`かつWriteあり。`schedule apply`は有効な**全Job**を登録・更新するため、自動実行しない。
- 全米株の条件なし全件取得はProvider制約で未対応。OHLCV・ニュース・財務を直接取得する専用CLI・定期取得Jobも未実装。Schemaに合うこととTradingViewで取得成功することは別。未実行の実機検証を成功扱いしない。

## 方式A：成果物と確認

1. 完全な`screenings/<name>.json`と、希望された場合は`jobs/<name>.json`を用意する。
2. 希望した条件とJSONフィールドの対応、未対応・未確認事項を短く説明する。
3. CodexはJSON構文・Schema・ファイル名・Job参照先をローカルで検証する。[load_screening_by_name](../../src/tradingview_screening/screening/validators.py)と[load_job_by_name・validate_job_screening_reference](../../src/tradingview_screening/jobs/loader.py)はMCPへ接続せず検証できる。Screeningの読込後は内部の`name`と指定ファイル名の一致も照合する。専用のvalidate CLIはない。利用可能なプロジェクト環境で検証し、未実行なら理由を報告する。
4. **利用者が実取得を依頼した後**はWindowsのコマンドプロンプトで`app.bat screen <screening_name>`、結果は`app.bat results latest <screening_name>`。`screen`はTradingView Readとローカル保存だけでWatchlistを更新しない。Jobなら`app.bat run <job_name>`。`enabled=false`でも手動runは実行する。結果参照は**Job名でなくScreening名**。失敗後の`latest`は古い成功結果の場合があるため日時も確認する。PowerShellは`.\app.bat`、Dockerは[Docker導入](DOCKER.md)を参照。
5. 修正依頼時は指定された条件だけを変え、既存ファイルを意図せず変更しない。

## 方式B：Pythonの再利用箇所と境界

**汎用pipelineエンジンや複合処理専用CLIは未実装です。** 自作Pythonは標準`screen`やJobの`task.definition`にファイル名・Tool名を指定しても実行できません。既存のbuiltinは任意Pythonを起動する仕組みではありません。

| 役割 | 再利用する既存実装・条件 |
| --- | --- |
| 公式MCP接続・型付き呼び出し | [TradingViewClient](../../src/tradingview_screening/integrations/tradingview/client.py)と[Request Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。既存の認証・接続経路を使う |
| OAuth・通信制御 | [auth.py](../../src/tradingview_screening/integrations/tradingview/auth.py)と[RequestGovernor](../../src/tradingview_screening/common/request_governor.py)。既存の資格情報管理、Rate Limit・Retry・Timeout・Concurrency・Cacheを通す |
| Screeningの取得・正規化 | [engine.py](../../src/tradingview_screening/screening/engine.py)と[正規化](../../src/tradingview_screening/integrations/tradingview/screener_normalization.py)。再利用できる単一取得段階に使用する |
| 結果保存 | [results.py](../../src/tradingview_screening/screening/results.py)。既存Screening結果契約に適合する場合だけ利用。任意Tool応答や外部データの自動保存・履歴比較はない |
| 管理Watchlist同期 | [watchlist_sync.py](../../src/tradingview_screening/screening/watchlist_sync.py)と[managed_watchlists.py](../../src/tradingview_screening/screening/managed_watchlists.py)。管理対象識別・差分・ロック・書込後確認を維持する |

独自HTTP認証・token保存、非公式TradingView API、TradingViewのスクレイピング・無断のブラウザ操作を追加しない。別MCPサーバー（`tvmcp`等）の導入を必須にしない。

Pythonラッパーの存在は、Providerで希望データを取得できる保証ではありません。`get_ohlcv`はOHLCV取得であり、公式RSI計算機能とは案内しません。`get_technicals_rating`の時間足指定も、希望するRSI14値が返る保証ではありません。列・時間足・期間を実資料で確認し、不明なら取得可能と断言しないでください。**配布用コアにOHLCVからRSI等を再計算する機能を先回り実装しません。**

### データと失敗を追跡する

- 外部の構成銘柄等は、出典URL、取得時刻（タイムゾーン付き）、対象日、母集団件数、欠落・重複、利用条件・ライセンス、取得制限と失敗時の挙動を示す。銘柄コードとTradingView symbolの対応・未照合件数も記録する。
- 段階ごとの入力・取得・除外・残存件数と欠損理由、ランキング基準・対象日・同順位の扱いを記録する。母集団の確認とランキング全体の網羅性は別に検証する。`totalCount`と`returnedCount`、上位N件と全件を区別する。最大1000行・未確認のページングを全件取得手段として案内しない。
- 日足出来高の対象日、RSIの出所・時間足・期間・更新時点、確定足/形成中の足を明示する。異なる日時の値を暗黙に同一視しない。時間足不明・欠損・部分取得なら「完全な上位100件」「全市場の該当銘柄」と報告しない。
- 保存する段階別結果、実行時刻、エラー、完全性の根拠、最終結果形式を決める。複合処理・外部データを単一Screeningのfingerprintや`source=tradingview_official_mcp`だけで表したことにしない。既存契約に合わなければ拡張側の別形式・保存先を示し、標準`results`で読めると偽らない。
- 取得失敗や部分成功を正常0件へ変換しない。**全段階の必要データと結果の妥当性を確認できない場合はWatchlist同期を中止する。** 既存の同期関数だけで複合処理全体の完全性が検証されるとは扱わない。

### 使える成果物として提供する

利用者のローカル拡張と製品本体へ一般化して取り込む変更を区別します。条件ごとの使い捨てPythonを本体`src/`へ増やさず、利用者と決めた拡張用フォルダに保存します。**実際に作成したファイルのパス、必要モジュール・依存、Python環境、作業ディレクトリと起動コマンド、検証方法、結果の保存先・読み方**を示してください。Windows Embedded PythonまたはDocker環境への組み込み可否も確認し、未検証の起動手順を動作済みとしないでください。

## ChatGPT・Codexの成果物と操作の境界

- **ChatGPT通常チャット**：完成JSONまたはPython・必要設定をダウンロード可能なファイルで渡す。生成機能が使えなければ完全な本文を提供し、保存先・保存手順を説明する。利用者PCへ自動設置・実行したとは説明しない。Pythonの編集・検証が必要ならCodex等のローカル環境へ引き継ぐ。
- **Codex**：アクセス可能なローカルのアプリフォルダへ保存・検証する。方式Aは構文・Schema・参照先、方式Bは構文・依存・処理順・欠損/失敗時の同期中止をローカルで確認する。必要な実行環境がなければ未検証範囲を示す。通常の条件作成にGitHubへのpush・PRは不要。
- **両方式共通**：選んだ方式と理由、作成ファイル、希望と設定の対応、未対応・未確認事項、検証済み範囲を短く報告する。未実行の実取得・テスト・Writeを成功扱いしない。修正時は指定された条件だけを変える。

**WriteとSchedulerは明示依頼がある場合だけ。** [Watchlist同期](WATCHLIST_SYNC.md)は銘柄の追加・削除を伴い、正常0件なら管理Watchlistを空にします。対象・差分と副作用を説明し、異常結果を空リストとして同期しないでください。Write失敗を自動再送・rollbackせず、token・認可code・credential・Provider生応答全文をチャットへ貼らないでください。

同梱`sample_screen_daily`は`enabled=true`かつ`watchlistSync=true`。`schedule apply`は**有効な全Job**を登録・更新するため、自分のJobだけでなく全定義を点検してください。定義を作っただけでは登録しません。[既存のProvider・CLI制約](FEATURES.md)は両方式で守ります。

## English note

Read the actual manuals, schemas, Provider-supported fields and bundled examples before choosing an implementation. Japanese documentation is authoritative. If files are inaccessible, ask for attachments or their contents; do not claim to have read them.

- **A — standard JSON, always preferred when sufficient:** Create `screenings/<name>.json`; add `jobs/<name>.json` only when requested. Supported market/filter/sort/limit/columns/symbolset/preset combinations do not need custom Python or BAT files. Japanese stocks with PER/yield filters, volume descending and limit 20 belong here. Clarify PER bounds and forecast versus TTM yield; the bundled `div_yield` filter uses forecast yield.
- **B — custom Python, only when a single Screening cannot express the request:** Fixing the Growth-market top 100 by daily volume, then filtering those symbols by 1-hour RSI14 <= 40 requires ordered stages. Filtering RSI before ranking changes the meaning. Explain why Python is needed and verify universe coverage, ranking completeness, indicator source/timeframe/period and timestamps before claiming feasibility.
- Reuse the existing official TradingView MCP client, OAuth, request governor, normalization, compatible result storage and managed Watchlist safeguards where applicable. No generic pipeline engine or custom-Python CLI/job runner is implemented. Wrappers do not guarantee Provider data availability. Do not invent filters, columns or APIs, require another MCP server, or add core RSI calculations in advance.
- For external data, report source, retrieval time, universe count, missing/unmatched symbols, limits and usage terms. Track counts and errors per stage. Never describe partial retrieval as a complete universe, or convert failure into a successful empty Watchlist sync. Custom results need an explicit format and storage path; standard result history does not automatically support them.
- ChatGPT provides complete files and save instructions; ordinary chat cannot install them on the user's PC. Codex saves and validates in an accessible local environment. For Python, provide actual paths, dependencies, interpreter, working directory, launch command and result-reading instructions. Report unverified steps honestly.
- File creation, offline validation, live reads and writes are separate actions. Keep Watchlist writes and scheduling disabled initially; never write to TradingView or register/remove scheduled tasks without explicit user instructions. Sync adds/removes symbols, and a valid empty result clears the managed Watchlist. The bundled `sample_screen_daily` enables writes; `schedule apply` affects **all enabled jobs**.

[AI CLI操作](AI_USAGE.md) / [利用者マニュアル](README.md)
