# Screening結果（Phase 6）

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
