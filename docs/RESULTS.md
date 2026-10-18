# Screening結果・履歴・米国セクター集計（Phase 6/9/11）

`python -m tradingview_screening screen <name>` は `screenings/<name>.json` を実行し、成功時にstdoutとファイルへ同じアプリJSONを返します。リポジトリ直下から実行してください。

## JSON契約

| Field | 内容 |
| --- | --- |
| schemaVersion | 1 |
| status | success / partial / failed |
| operation | screening |
| name | Screening名 |
| executedAt | Asia/Tokyo、timezone-aware ISO 8601 |
| source | tradingview_official_mcp |
| metadata.requestedCount | 定義のlimit。定義検証前の失敗はnull |
| metadata.requestedLimit | 成功時の定義のlimit。requestedCountを互換目的で維持 |
| metadata.totalCount | Providerが返した要求条件に対する総件数 |
| metadata.returnedCount | 正規化後の行数 |
| metadata.limitReached | returnedCountがrequestedLimitに達したか |
| metadata.completeCoverage | returnedCountと一意symbol数がtotalCountに一致するか |
| metadata.definitionFingerprint | 新規成功結果の定義識別情報。version / algorithm / value |
| metadata.partial | 安全な部分結果の場合のみtrue |
| metadata.durationMs | 実行の経過時間（ミリ秒） |
| results | symbolと定義で指定したcolumnsの行データ |
| errors | secret-freeなアプリerror |

`cacheHit` はRequestGovernorから実測情報を取得できないため省略します。Phase 6では不整合な応答全体をfailedにし、partial結果は生成しません。limitに達した通常の結果をpartialとは扱いません。

追加した4項目は成功結果に一組で付けます。totalCount=503 / returnedCount=5 / requestedLimit=5なら、limitReached=true / completeCoverage=falseです。totalCount=5 / returnedCount=5なら両方trueになります。completeCoverageは要求条件内の件数一致であり、全市場や別Universeの完全性は意味しません。

従来の4項目を持たない保存結果も読み込めます。新項目が一部だけある、型が不正、件数・flagが矛盾する結果はlatest/保存/同期で拒否します。既存の上位N件のWatchlist同期はcompleteCoverage=falseでも利用できます。

## Response正規化

2026-09-26の少量Readで、`structured_content.success=true`、`data.rows`（object配列）、`data.totalCount`（整数）、行の`symbol`とサンプル要求列を実測しました。空配列も正常です。

Providerの未知の追加fieldは許容し、保存対象はsymbolと要求列へ限定します。要求列の欠落や構造の不一致を補完せず、`MCP_SCHEMA_MISMATCH`を返します。`content`のテキストはJSONとして読み直しません。

`data.ignored_filters` が存在する場合は空配列だけを受理します。非空または型不正は、success=trueでも `MCP_SCHEMA_MISMATCH` とし、結果保存・Watchlist同期へ進めません。エラーにはProvider本文を含めません。

`structured_content.success=false` はProvider業務失敗です。MCP transport失敗・OAuth失敗・MCP `is_error` と区別し、生本文を出さずアプリerrorに正規化します。全市場・全columnsのshapeを実測したものではありません。

## 保存とlatest

保存先は `results/YYYY-MM-DD/<name>_<HHMMSS>.json` です。日付・時刻はexecutedAtをAsia/Tokyoへ変換します。同じ秒に実行した場合は `_1.json`、`_2.json` のように連番を加えます。

同じ日付フォルダの一時ファイルへJSONを書き、flush/fsync後にhard linkで非上書き公開します。hard link非対応など公開に失敗する環境では保存エラーを返します。既存ファイルを上書きするfallbackは行いません。failed結果は保存しません。

```text
python -m tradingview_screening results latest
python -m tradingview_screening results latest sample_standard_screen
```

全日付フォルダから、名前指定時はそのScreeningだけを検索します。アプリEnvelope、日付・名前・時刻の整合性を検証し、executedAtの絶対時刻で比較します。同時刻は衝突連番等で決定的に比較します。directory mtimeは使いません。

壊れたJSON、無関係なJSON、failed結果、外部を指すリンクを採用しません。有効結果がない場合は明示的なアプリerrorです。Screening名へパスを指定することはできません。

`results/` はGit管理外です。結果にはMCP raw response全量・content・Providerエラー本文を保存しません。Watchlist同期・Jobs・SchedulerはPhase 6の対象外です。

## 定義fingerprint（Phase 11）

新規成功結果の `metadata.definitionFingerprint` は次の形式です。

```json
{"version":1,"algorithm":"sha256","value":"64桁の小文字16進数"}
```

検証済み定義から `market` / `symbolTypes` / `filters` / `filterPreset` / `symbolset` / `sortBy` / `sortOrder` / `limit` / `columns` の9項目を取り出します。省略項目もモデルの既定値（null等）を含め、JSONを `sort_keys=True` / `separators=(",", ":")` / `ensure_ascii=False` / `allow_nan=False` で生成し、UTF-8のSHA-256を計算します。

objectのキー順は正規化し、配列順は保持します。結果行の並び替えは銘柄差分に影響しませんが、定義のcolumnsやsymbolset等の配列順を変えた場合は保守的に別fingerprintとなります。name、description、Watchlist設定、実行時刻、取得データ値はhash対象外です。

旧JSONを移行・削除しません。fingerprintがない結果も `latest` と履歴で読めますが、条件同一性を検証できないため比較には使えません。現在の定義から古い結果へfingerprintを補いません。未対応のversion/algorithmは比較不可です。

## 履歴

```bat
app.bat results history public_japan_value
app.bat results history public_japan_value --limit 10
```

保存済みの成功かつ検証済み結果を、新しい順に返します。limitは既定20、1〜1000です。0件なら空のitemsで正常終了します。

`operation=screening_history` のEnvelopeの `items` に、プロジェクト相対POSIX形式のfile、executedAt、returnedCount、totalCount、completeCoverage、definitionFingerprintを返します。旧結果の未記録項目はnullです。Provider総件数と取得行数を同じ意味では使いません。

日付folder・filename・executedAtの整合性、非有限数、結果metadataを検証します。壊れたJSON、failed/partial結果、symlinkや対象外pathは除外します。時刻はUTCへ変換して降順、同時刻は衝突連番の数値、filenameで決定的に並べます。mtimeは使いません。

## 前回比較

```bat
app.bat results compare public_japan_value
```

保存済みの直近2件の成功snapshotを選び、古い方をfrom、新しい方をtoとします。現在のScreening定義ファイルやMCPは参照しません。fingerprint、symbol重複、coverage flagの整合等は選択後に検証するため、最新または直前が比較不能でも古い比較可能ペアへ飛びません。破損JSON・基本Envelope不整合・危険なpathは履歴と同様に比較候補から除外します。

比較成功は `operation=screening_compare` / `status=success` の独立Envelopeです。両snapshotのfile・日時・fingerprint・coverage、fingerprintMatched、observedAdded / observedRemoved / observedCommon、indicatorChanges、totalCountChangeを返します。symbolは `EXCHANGE:TICKER` を変換せず厳密キーにし、重複は拒否します。symbol・列の出力順は辞書順です。

indicatorChangesは `{symbol, fields: {列名: {before, after}}}` の配列です。before/afterは `{present:true,value:...}`、未記録の列は `{present:false}` とし、欠落とnullを区別します。指標値は有限number、string、boolean、nullを扱い、複合object/arrayは比較不可です。numberの1と1.0は同値、booleanのtrueとnumberの1は異なる値として扱います。

comparisonScopeはcoverageが両方trueなら `full_matched_set`、それ以外は `observed_set_only` です。不完全なtop-Nから見えなくなった銘柄を、条件不適合とは断定しません。totalCountChangeはProvider総件数の差であり、observedAdded / Removedの件数差とは区別します。旧coverageで総件数不明なら差はnullです。

比較対象不足、fingerprint欠落・不一致・未対応形式、不正symbol・重複等は `status=not_comparable` と理由を返し、exit 1になります。履歴成功・比較成功はexit 0、引数の誤りはexit 2です。raw例外やProvider本文を出しません。

| reason | 意味 |
| --- | --- |
| NO_BASELINE | 成功snapshotが2件未満 |
| MISSING_FINGERPRINT | 旧結果等でfingerprint未記録 |
| INVALID_FINGERPRINT | fingerprintが不正型・不正形式 |
| UNSUPPORTED_FINGERPRINT | version/algorithmが未対応 |
| DEFINITION_MISMATCH | 実行条件のfingerprint不一致 |
| INVALID_SYMBOLS | symbol形式不正または重複 |
| INVALID_VALUES | 指標値が複合object/array等で比較対象外 |
| INVALID_METADATA | 選択後のcoverage等の整合検証に失敗 |

不正形式のfingerprintは比較参照ではnullへ置き換え、不正な本文を出しません。比較不能のEnvelopeには銘柄差分を生成しません。今後の `screen` / `run` が生成する同条件の新しい2結果が揃ってから比較できます。

### 架空データの出力例

[比較JSONの全体例](examples/screening_compare_synthetic.json)は、専用検証ディレクトリに作成した架空結果をWindows Embedded Pythonと共通app.batで比較した出力です。市場データではありません。観測集合ではTEST:BBBが出現、TEST:CCCが今回未観測、共通TEST:AAAのcloseが100から105、volumeが10から12へ変わり、Provider総件数は12から13です。

```json
{"status":"success","comparisonScope":"observed_set_only","observedAdded":["TEST:BBB"],"observedRemoved":["TEST:CCC"],"observedCommon":["TEST:AAA"],"totalCountChange":1}
```

上記は出力の抜粋です。実行例は `app.bat results compare observed_sample`、exit 0でした。旧fingerprintなしの2結果はMISSING_FINGERPRINT、limitを変更した2結果はDEFINITION_MISMATCHでexit 1を確認しました。既存public_japan_valueは保存結果1件のためhistory/latestはexit 0、compareはNO_BASELINE / exit 1でした。比較のためのMCPアクセスは行っていません。

履歴・比較はローカルread-onlyです。TradingView MCP・認証情報・Watchlist・Alert・Schedulerを操作しません。差分ファイルを自動保存せず、既存結果ファイルも変更しません。

## 米国セクターsummary（Phase 9）

`us_sector_daily`は`america / stock`全Universeからsector/changeを取得するbuiltinです。sample Jobは`us_sector_morning`（daily 07:00 JST、現行Betaはenabled=false）。1 symbol = 1票のequal weightでsector別算術平均を計算し、時価総額加重は行いません。

| Field | 内容 |
| --- | --- |
| schemaVersion / status | 1 / success（正常summaryのみ保存） |
| operation / name | us_sector_summary / us_sector_daily |
| retrievedAt | timezone-aware取得時刻 |
| source | tradingview_official_mcp |
| metadata.market / symbolTypes | america / ["stock"] |
| metadata.changeMetric | tradingview_change_snapshot_percent |
| metadata.validSymbolCount | 有効なunique symbol数 |
| metadata.excludedRowCount | sector/change欠損で除外したunique symbol数 |
| metadata.sectorCount | 出力sector数 |
| metadata.sessionAssumption | 米国regular session終了後に実行し、返されたsnapshotを使う運用前提 |
| results | rank / sector / meanChange / sampleSize |
| errors | 正常時は空配列 |

`meanChange`は有限の算術平均、`sampleSize`はそのsectorの有効unique symbol数です。入力順序に依存しません。平均降順、数値完全一致の同率はcompetition ranking（1, 1, 3）、同率の表示順はsector名昇順です。表示丸めで同率を作りません。

同一symbol・同じsector/changeの重複は1票、矛盾する重複は`MCP_SCHEMA_MISMATCH`。sectorの前後空白は除去します。sector/changeの不在・nullは除外しますが、片側欠損でも他方の型を検証します。空sector、bool、NaN、Inf、不正型・row構造・symbolはschema mismatchであり、ゼロや欠損に置き換えません。同一欠損symbolの重複はexcludedRowCountでも1件です。

休日・早期終了calendarは導入せず、regular session終了前の実行でも数値を改変しません。retrievedAtとsessionAssumptionから実行条件を確認してください。OHLCVからの再計算、ニュース理由分析は行いません。

### Coverageと実Provider確認

2026-09-27、通常Windowsユーザー + Embedded Python 3.12.8でread-only確認しました。

| 確認 | 結果 |
| --- | --- |
| app.bat mcp status | 認証・Tool Discovery成功、server 1.30.0 / protocol 2025-11-25 |
| 実list_tools | 35 tools。run_screenerは上限1000、offset/page/cursorなし |
| get_screener_columns | market=stock、search=sector/changeで各完全一致nameとstock対応を確認 |
| 最小run_screener | market=america、symbol_types=["stock"]、columns=["sector","change"]、limit=1はsuccess=false、dataなし |
| 空filters / 明示sort | filters={}、さらにchange/descを指定してもfilterを要求する業務失敗 |
| 全Universe・US実row・totalCount | 未検証。正式な完全取得手段は確認できず |
| live Job実行・保存 | coverage未確定のため未実行。成功保存を確認したとは扱わない |

[公式MCP資料](https://www.tradingview.com/mcp/docs)も上限1000件を示します。field discoveryはstructured_content.columnsのname/marketsを使用します。Screener正規化はPhase 6で観測済みのstructured_content.data.rows/totalCountを基礎とし、US成功応答はUnit Testで検証します。US実測と他市場での過去の観測を混同しません。市場データ値や生エラー本文は記録しません。

全Universe契約は維持し、S&P 500・NASDAQ・先頭1000件へ縮小しません。Universeを変えるfilterや大量分割queryで回避しません。成功応答でもreturnedCountはlen(rows)から算出し、非負整数totalCountと比較します。小さければ`US_SECTOR_COVERAGE_INCOMPLETE`、大きい・不正型なら`MCP_SCHEMA_MISMATCH`です。unique symbol数も照合し、重複で未取得銘柄を隠しません。完全性を確認する前に集計・保存しません。

### 2026-10-18の再判定

既存Python TradingViewClient / 共通RequestGovernorでDiscoveryと少量Readを再実行しました。protocol 2025-11-25、server 1.30.0、35 Tool、Screener schemaは同一です。sector/changeはstock対応、S&P 500 filterとsymbolsetは各totalCount=503 / returnedCount=5で、symbol・sector・changeを持つobject行を確認しました。

一方、filter/preset/symbolsetを全省略したamerica/stockはsuccess=falseでした。上限1000件、pagination/offset/cursorなしのため全米株を完全取得する公式手段は未確認です。S&P 500は限定Universeとしてのみ成功扱いにし、全米株集計のlive実行・保存は行っていません。Issue #18 / PR #19のblocking limitationとDraftを維持します。一般Screening拡張は独立Issue #22 / PR #23で管理します。

### Job接続と保存

Job stdoutはoperation=job、task.type=builtin、task.definition=us_sector_dailyとし、`builtin`に上記summaryを格納します。save=trueならsummaryだけを`results/YYYY-MM-DD/us_sector_morning_HHMMSS.json`へ保存し、Job.metadata.saved=true / resultPathに相対パスを返します。日付・時刻はretrievedAtをAsia/Tokyoへ変換します。同秒suffix、非上書きatomic publish、有限JSONとpath safetyはScreening保存と同じ契約です。

save=falseでは取得・集計のみ、metadata.saved=false / resultPath=nullです。Provider失敗・coverage不足・型破損時はJob failed / exit1で保存しません。AUTH_REQUIREDはexit3、builtinのwatchlistSync=trueはCONFIG_VALIDATION_ERROR / exit2。未知builtinはJOB_TASK_UNAVAILABLEです。raw responseは渡しません。

`results latest`は既存Screening専用のままです。builtin結果はJobのresultPathを使用してください。全Universe取得とlive保存の未達はblocking limitationとして追跡し、Phase 9全体の完了とは扱いません。

### 2026-10-18 23:02〜23:03 JST 追加実機確認

- 本番の `app.bat run us_sector_morning`：現行公式MCPは条件なしの `america/stock` 取得を拒否し、`PROVIDER_ERROR` / exit 1、JSON保存なし。実行と通信は正常に到達。
- 検証専用S&P 500：`filters.index="S&P 500"`、`totalCount=returnedCount=uniqueSymbolCount=503`、無視されたfilterなし。TradingView sector分類20件、有効503件・除外0件。各平均・件数・rankを独立照合し、JSON保存と読み戻し成功。
- これは **S&P 500限定での成功** であり、全米株本番summaryの成功ではない。Beta公開サンプルは `enabled=false` とし、Provider更新により全Universeの取得方法が確立するまで定期登録しない。
- [Issue #18の検証根拠](https://github.com/TakamKaji/tradingview_mcp_support/issues/18#issuecomment-6250858944) を参照。
