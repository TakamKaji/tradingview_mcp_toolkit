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
