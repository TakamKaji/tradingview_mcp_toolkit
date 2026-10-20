# 自分のスクリーニング条件を作って実行する

Screeningは対象市場・条件・並び順・取得列をJSONで定義し、共通の`screen`コマンドで実行する機能です。日本株割安やS&P 500は同梱の使用例で、選べる条件がそのサンプルだけに固定されているわけではありません。

## 自分の条件を追加する

ここでは日本株・PER 0〜15・予想配当利回り3%以上・出来高降順という条件を、独立した名前で作ります。

1. 展開フォルダの`screenings/public_japan_value.json`をコピーし、同じ`screenings/`内に`my_japan_value.json`として保存します。
2. 内部の`name`を`my_japan_value`に変えます。ファイル名の拡張子を除いた部分と一致させます。
3. 下の全文例を参考に条件を編集します。この例では上限を20件にし、Watchlist同期は無効にしています。
4. **UTF-8（BOMなし）**で保存します。末尾が`.json.txt`にならないよう注意してください。JSONにはコメントや末尾の余分なカンマを書けません。

名前には先頭が半角英数字で、その後は半角英数字・`_`・`-`を使えます。空白、日本語、パス区切り、`.`、Windows予約名（`CON`、`NUL`等）は使いません。同名の既存サンプルを上書きせず、別名で保存してください。

`screenings/my_japan_value.json`の全文：

```json
{
  "schemaVersion": 1,
  "name": "my_japan_value",
  "description": "自分用の日本株PER・予想配当条件",
  "market": "japan",
  "symbolTypes": ["stock"],
  "filters": {
    "pe": [0, 15],
    "div_yield": [3, null]
  },
  "sortBy": "volume",
  "sortOrder": "desc",
  "limit": 20,
  "columns": [
    "close",
    "change",
    "price_earnings_ttm",
    "dividends_yield",
    "RSI",
    "volume"
  ],
  "watchlist": {"enabled": false}
}
```

## 各項目の設定

| 項目 | 指定方法 |
| --- | --- |
| schemaVersion | 整数`1` |
| name | ファイル名と同じScreening名。コマンドには拡張子を付けない |
| description | 任意の説明文字列。省略可能 |
| market | `japan`、`america`等、Providerの市場名。空文字は不可 |
| symbolTypes | 空でない文字列の配列。この例は株式の`["stock"]` |
| filters | 下記の数値範囲、または対応する特殊キーの文字列 |
| filterPreset | 任意の公式preset。省略可能。選べる値は下記参照 |
| symbolset | 任意の対象銘柄集合。空でない文字列の配列。省略可能 |
| sortBy | 並べ替えに使う列。この例は出来高の`volume`。省略時はProviderの既定動作 |
| sortOrder | `desc`（降順）または`asc`（昇順）。省略時は`desc` |
| limit | 整数1〜1000。取得する上限であり、総該当件数とは別 |
| columns | 取得する列名の空でない配列。各列名も空にできない |
| watchlist | 任意。`enabled=false`または項目自体の省略で同期無効。`true`では`name`が必須 |

ローカルで市場名・種別・列名を文字列として受理しても、すべての組合せで取得できる保証はありません。**実際の対応市場・種別・filter・列はProviderに従います。** 未知のJSONキーはエラーです。

### 数値範囲とnull

通常の数値filterは`[下限, 上限]`です。`[0, 15]`は0〜15、`[3, null]`は3以上、`[null, 15]`は15以下を指定します。`null`はその側の制限なしで、0や空文字の代わりではありません。

両方`null`、下限が上限を超える範囲、数値の代わりの文字列やboolean、NaN/Infinityは使えません。`gt`等の独自演算子オブジェクトは受け付けません。`index`、`sector`、`industry`、`analyst_rating`だけは空でない文字列を指定します（例：`"index": "S&P 500"`）。

filter名と取得列名が同じとは限りません。この日本株例はfilterに公式aliasの`pe`・`div_yield`を使い、列には`price_earnings_ttm`・`dividends_yield`を指定します。`div_yield`は**予想配当利回り**の条件で、TTM配当利回りとは区別してください。列名として存在する`dividends_yield_ttm`をfilterへ流用しても、条件が無視される場合があります。

### filterPresetとsymbolset

`filterPreset`は`pullback_with_reversal`、`breakout_with_volume`、`oversold_healthy`、`earnings_runup`、`relative_strength`、`new_highs`の6値です。具体例は`public_oversold_healthy.json`を参照してください。各presetの条件を本ツールが独自計算するわけではありません。

`symbolset`の例は`["SYML:SP;SPX"]`です。これは公式のS&P 500対象集合の指定例です。空配列は不可です。filters・filterPreset・symbolsetは同時指定できますが、組合せの意味と対応可否はProviderが決めます。

### 取得列・上限・Watchlist

`columns`は表示したいProviderの列を選びます。`close`、`change`、`volume`など、まず同梱例の列を使い、変更時は[公式MCP資料](https://www.tradingview.com/mcp/docs)の対応範囲を確認してください。全列を列挙する専用CLIはありません。詳しい列の探索はPython APIの`get_screener_columns`を使う範囲です（[利用方法の違い](FEATURES.md#c-公式toolと本ツールの接続範囲)）。Tool一覧を表示する`mcp tools`と、取得列の一覧は別です。

`limit=20`でも実際の取得が20件未満になる場合があります。`totalCount`は条件に対するProvider総件数、`returnedCount`は実取得行数です。上限まで取れただけでは全件取得とは限りません。`completeCoverage=true`も指定した条件内の完全性で、市場全体の保証ではありません。

Watchlistへ同期するには、Screeningの`watchlist.enabled=true`・`name`と、Jobの`output.watchlistSync=true`を設定します。どちらかが無効ならJobの同期は行われません。`screen`は設定が有効でも取得とローカル保存だけです。同期は銘柄の追加・削除を伴い、正常0件なら管理Watchlistを空にします。

## 作成した条件を実行する

展開フォルダでコマンドプロンプトを開いて実行します。PowerShellでは`app.bat`を`.\app.bat`に置き換えてください。

```bat
app.bat screen my_japan_value
app.bat results latest my_japan_value
```

最初のコマンドはTradingView ReadとPC内へのJSON保存、次は保存結果の読み取りです。成功時は`results/YYYY-MM-DD/`へ保存されます。履歴・比較は[Results](RESULTS.md)を参照してください。この名前は上の手順で作成して初めて使える例で、同名ファイルは最初から同梱されていません。

## 同梱サンプルからコピー元を選ぶ

別の条件から始めたい場合は、次の例をコピー元に選べます。

| コピー元（screenings内） | 使用例 | 取得上限 |
| --- | --- | --- |
| [public_japan_value.json](../../screenings/public_japan_value.json) | 日本株、PER 0〜15・予想配当利回り3%以上 | 5 |
| [public_sp500.json](../../screenings/public_sp500.json) | 米国、S&P 500をindexで指定 | 5 |
| [public_oversold_healthy.json](../../screenings/public_oversold_healthy.json) | 米国、公式oversold_healthy preset | 5 |
| [public_sp500_symbolset.json](../../screenings/public_sp500_symbolset.json) | 米国、symbolsetでS&P 500を指定 | 5 |
| [sample_standard_screen.json](../../screenings/sample_standard_screen.json) | 日本株条件・追加列とWatchlist設定の例 | 50 |

public系4例はWatchlist無効です。`sample_standard_screen`はWatchlist設定が有効ですが、**`screen`単体は同期しません**。Jobから同期を有効にした場合との違いは[Watchlist](WATCHLIST_SYNC.md)を確認してください。サンプルの件数・条件は利用者が変更できる設定値です。

## 失敗したとき

| 状況 | 対処 |
| --- | --- |
| 定義が見つからない | 展開フォルダから実行したか、`screenings/my_japan_value.json`があるか確認 |
| CONFIG_JSON_INVALID | UTF-8 BOMなし、引用符、カンマ、括弧を確認。コメントは削除 |
| CONFIG_NAME_INVALID | ファイル名・コマンド名に空白やパスを含めず、予約名も避ける |
| CONFIG_VALIDATION_ERROR | nameとファイル名の一致、必須項目、未知キー、型、範囲を確認 |
| AUTH_REQUIRED | `app.bat mcp auth`で正規の認証を行う |
| Provider拒否・MCP_SCHEMA_MISMATCH | 市場と条件・列の組合せ、条件無視や不整合を確認。失敗を0件成功に読み替えない |

定義・引数のエラーは通常exit 2、実行時失敗は1、再認証要求は3です。JSONの`errors`と[トラブル対応](TROUBLESHOOTING.md)を確認します。失敗結果は保存しないため、`latest`が以前の成功結果を返す可能性があります。必ず実行日時も確認してください。

## 公式MCP Beta版のスクリーニング制限（2026-10-18実機確認）

**全米株`america/stock`の条件なし一括取得は、TradingView公式MCP Providerがリクエストを拒否するため利用できません。** OAuth障害や本ツール独自の制限とは区別します。`run_screener.limit`は最大1000行で、全件取得用のoffset/page/cursorは確認できていません。完全取得できない集合を全米株集計として表示せず、`us_sector_morning.enabled=false`を維持しています。

S&P 500限定503銘柄・20分類の集計と保存を確認した過去の検証は、全米株成功を意味しません。この限定集計を提供する製品Jobも同梱していません。条件付きScreeningは利用できますが、成功可否・件数はProviderと条件に依存します。Betaの仕様は変更される可能性があります。

[自分のJobを作る](SCHEDULE_MANUAL.md#自分のjobを作る) / [利用者マニュアル一覧](README.md)
