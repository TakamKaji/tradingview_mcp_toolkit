# Screening結果と米国セクターsummary

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
| metadata.returnedCount | 正規化後の行数 |
| metadata.partial | 安全な部分結果の場合のみtrue |
| metadata.durationMs | 実行の経過時間（ミリ秒） |
| results | symbolと定義で指定したcolumnsの行データ |
| errors | secret-freeなアプリerror |

`cacheHit` はRequestGovernorから実測情報を取得できないため省略します。Phase 6では不整合な応答全体をfailedにし、partial結果は生成しません。limitに達した通常の結果をpartialとは扱いません。

## Response正規化

2026-09-26の少量Readで、`structured_content.success=true`、`data.rows`（object配列）、`data.totalCount`（整数）、行の`symbol`とサンプル要求列を実測しました。空配列も正常です。

Providerの未知の追加fieldは許容し、保存対象はsymbolと要求列へ限定します。要求列の欠落や構造の不一致を補完せず、`MCP_SCHEMA_MISMATCH`を返します。`content`のテキストはJSONとして読み直しません。

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

## 米国セクターsummary（Phase 9）

`us_sector_daily`は`america / stock`全Universeからsector/changeを取得するbuiltinです。sample Jobは`us_sector_morning`（daily 07:00 JST）。1 symbol = 1票のequal weightでsector別算術平均を計算し、時価総額加重は行いません。

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

### Job接続と保存

Job stdoutはoperation=job、task.type=builtin、task.definition=us_sector_dailyとし、`builtin`に上記summaryを格納します。save=trueならsummaryだけを`results/YYYY-MM-DD/us_sector_morning_HHMMSS.json`へ保存し、Job.metadata.saved=true / resultPathに相対パスを返します。日付・時刻はretrievedAtをAsia/Tokyoへ変換します。同秒suffix、非上書きatomic publish、有限JSONとpath safetyはScreening保存と同じ契約です。

save=falseでは取得・集計のみ、metadata.saved=false / resultPath=nullです。Provider失敗・coverage不足・型破損時はJob failed / exit1で保存しません。AUTH_REQUIREDはexit3、builtinのwatchlistSync=trueはCONFIG_VALIDATION_ERROR / exit2。未知builtinはJOB_TASK_UNAVAILABLEです。raw responseは渡しません。

`results latest`は既存Screening専用のままです。builtin結果はJobのresultPathを使用してください。全Universe取得とlive保存の未達はblocking limitationとして追跡し、Phase 9全体の完了とは扱いません。
