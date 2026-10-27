# 公式MCP機能マニュアル

調査基準日：**2026-10-26 JST**。基点develop：`0a8cf09`（PR #62マージ済み）。[公式MCP資料](https://www.tradingview.com/mcp/docs)と既存Client/Request/Responseを照合した利用者向け機能解説の正本です。公式ページの転載ではなく、本リポジトリでの使い分けを説明します。

## このリポジトリと公式MCPの関係

利用者はTradingView公式MCPをAIへ別途登録しません。通常のScreeningは既存CLIと標準JSON、複合処理は既存`TradingViewClient`と型付きRequestを使います。認証・Rate Limit・Retry等を再実装せず、AIが任意のMCP connectorを直接操作する前提にしません。

入口は[Windows導入](WINDOWS_SETUP.md)、対応境界の要約は[FEATURES](FEATURES.md)、条件を選ぶ時は[条件カタログ](SCREENER_CONDITIONS.md)、JSON/Pythonの判断と実行契約は[AIガイド](AI_JSON_GUIDE.md)です。[Screening操作](SCREENING_MANUAL.md)・[Job](SCHEDULE_MANUAL.md)・[Watchlist同期](WATCHLIST_SYNC.md)の操作説明を全文複製しません。

## 調査範囲と証拠の読み方

公開ページの35 Toolと既存35ラッパー/Requestは名前が対応しています。下表の「正式名」は公開ページの論理名で、Pythonメソッド名も同じです。実サーバーのwire名は`mcp-tv-*`/`mcp-watchlist-*`へ既存[tool_catalog.py](../../src/tradingview_screening/integrations/tradingview/tool_catalog.py)が変換します。

**公式仕様確認・Schema静的確認・Discoveryでの存在確認・Tool実行成功を区別**します。仕様確認は権限や実データの成功保証ではありません。今回の接続/実機結果は末尾の確認状態に記載し、未実施のToolを動作確認済みとしません。過去の実測はその日付を併記します。

## 利用経路と安全区分

| 記号 | 標準CLI | Python | Job / Scheduler |
| --- | --- | --- | --- |
| S | `screen` | 対応 | Screening JobとWindows日次Schedulerに接続 |
| W | 任意Tool用CLIなし | 対応 | 管理Watchlist同期内部のget/create/add/removeのみ。同期の明示依頼が必要 |
| C | 任意Tool用CLIなし | 対応 | 列探索は全米株builtin内部でも利用するが、その取得JobはProvider制約で無効。汎用取得Jobなし |
| P | 任意Tool用CLIなし | 対応 | 任意取得/操作Jobなし。Pythonを標準screenやJob名に指定しても起動しない |

`mcp tools`は一覧であり、任意Tool実行CLIではありません。Read＋ローカル保存は依頼された実行範囲、Watchlist/Alert Write・Scheduler登録/削除・認証情報削除は明示依頼がある場合だけです。`get_active_watchlist`はRead表記でも選択/作成の副作用があり、無副作用な接続確認に使いません。

## 全Tool索引

| 正式名 / Pythonメソッド | 分野 | 区分 | 利用経路 | 型付きRequest |
| --- | --- | --- | --- | --- |
| [list_watchlists](#list_watchlists) | Watchlists | Read | P | `ListWatchlistsRequest` |
| [get_watchlist](#get_watchlist) | Watchlists | Read | W | `GetWatchlistRequest` |
| [get_active_watchlist](#get_active_watchlist) | Watchlists | Read・副作用注意 | P | `GetActiveWatchlistRequest` |
| [create_watchlist](#create_watchlist) | Watchlists | Write | W | `CreateWatchlistRequest` |
| [delete_watchlist](#delete_watchlist) | Watchlists | Write | P | `DeleteWatchlistRequest` |
| [add_to_watchlist](#add_to_watchlist) | Watchlists | Write | W | `AddToWatchlistRequest` |
| [remove_from_watchlist](#remove_from_watchlist) | Watchlists | Write | W | `RemoveFromWatchlistRequest` |
| [update_watchlist](#update_watchlist) | Watchlists | Write | P | `UpdateWatchlistRequest` |
| [get_ohlcv](#get_ohlcv) | Market data / OHLCV | Read | P | `GetOhlcvRequest` |
| [get_economic_data](#get_economic_data) | Economic data | Read | P | `GetEconomicDataRequest` |
| [get_economic_symbols](#get_economic_symbols) | Economic data | Read | P | `GetEconomicSymbolsRequest` |
| [search_symbols](#search_symbols) | Symbol search | Read | P | `SearchSymbolsRequest` |
| [get_symbol_data](#get_symbol_data) | Screener | Read | P | `GetSymbolDataRequest` |
| [run_screener](#run_screener) | Screener | Read | S | `RunScreenerRequest` |
| [get_symbol_data_batch](#get_symbol_data_batch) | Screener | Read | P | `GetSymbolDataBatchRequest` |
| [get_screener_columns](#get_screener_columns) | Screener | Read | C | `GetScreenerColumnsRequest` |
| [get_technicals_rating](#get_technicals_rating) | Screener | Read | P | `GetTechnicalsRatingRequest` |
| [get_news](#get_news) | News | Read | P | `GetNewsRequest` |
| [get_news_story](#get_news_story) | News | Read | P | `GetNewsStoryRequest` |
| [get_forecasts](#get_forecasts) | Fundamentals & forecasts | Read | P | `GetForecastsRequest` |
| [get_financials](#get_financials) | Fundamentals & forecasts | Read | P | `GetFinancialsRequest` |
| [get_financial_history](#get_financial_history) | Fundamentals & forecasts | Read | P | `GetFinancialHistoryRequest` |
| [get_documents](#get_documents) | Documents | Read | P | `GetDocumentsRequest` |
| [get_document_view](#get_document_view) | Documents | Read | P | `GetDocumentViewRequest` |
| [get_earnings_calendar](#get_earnings_calendar) | Calendars | Read | P | `GetEarningsCalendarRequest` |
| [get_economic_calendar](#get_economic_calendar) | Calendars | Read | P | `GetEconomicCalendarRequest` |
| [get_dividends_calendar](#get_dividends_calendar) | Calendars | Read | P | `GetDividendsCalendarRequest` |
| [create_alert](#create_alert) | Alerts | Write | P | `CreateAlertRequest` |
| [update_alert](#update_alert) | Alerts | Write | P | `UpdateAlertRequest` |
| [delete_alert](#delete_alert) | Alerts | Write | P | `DeleteAlertRequest` |
| [stop_alerts](#stop_alerts) | Alerts | Write | P | `StopAlertsRequest` |
| [restart_alerts](#restart_alerts) | Alerts | Write | P | `RestartAlertsRequest` |
| [list_alerts](#list_alerts) | Alerts | Read | P | `ListAlertsRequest` |
| [get_alerts](#get_alerts) | Alerts | Read | P | `GetAlertsRequest` |
| [get_alerts_log](#get_alerts_log) | Alerts | Read | P | `GetAlertsLogRequest` |

## 引数・応答の共通規則

以下の引数表は**現行ローカルRequestが受理する契約**です。必須はキーの省略不可、省略可は送信しない選択が可能という意味で、明示nullの許可は型にnullがある場合だけです。ローカルのdefault=Noneを、Providerにnullを渡す指示やサーバー既定値と解釈しません。`Client`は明示指定フィールドを送ります。未知引数は原則拒否し、Alertの特定追加キーだけは別扱いです。

「公式既定」は公開ページに明記された値だけを記載し、「未記載」はProviderの既定値が不明です。型や上限に通っても意味・対応市場・フィルタ適用・利用権限は別途検証します。日付をstringとして受理することと、Providerの期間指定に適合することも別です。

全メソッドは非同期です。`TypedToolResponse`は`structured_content`と`content`を分離します。`ObservedReadResponse`はその内側のsuccess/error/count/missing_count等を型検証し、Tool別の追加データを保持します。これは足/記事/銘柄の完全固定Schemaではありません。型付き包絡を配列として扱わず、実応答・success/partial/missing・単位/日時/欠損を確認してください。下記の「主な内容」は用途の説明で、全キーの存在保証ではありません。

## Watchlists

### list_watchlists

自分のWatchlistの識別子と名前を調べる。利用例：同期対象の既存リストを利用者が確認する。

既存ラッパー：`TradingViewClient.list_watchlists()` / `ListWatchlistsRequest`。応答：`TypedToolResponse`。主な内容：一覧の項目構造は実応答で確認。

引数なし。

根拠：[公式のlist_watchlists](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### get_watchlist

IDを指定して銘柄集合を読む。利用例：既知IDの登録銘柄と差分を確認する。

既存ラッパー：`TradingViewClient.get_watchlist()` / `GetWatchlistRequest`。応答：`TypedToolResponse`。主な内容：リスト情報・銘柄。共有リストはread_onlyの確認も必要。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `watchlist_id` | 必須 | string | 未記載 |

根拠：[公式のget_watchlist](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### get_active_watchlist

現在選択中のWatchlistを得る。利用例：利用者がactive切替等も依頼した時に利用。

既存ラッパー：`TradingViewClient.get_active_watchlist()` / `GetActiveWatchlistRequest`。応答：`TypedToolResponse`。主な内容：active情報。未選択時の切替・未作成時の作成に注意。

引数なし。

**Read分類でも副作用あり：今回のRead-only調査から除外。**

根拠：[公式のget_active_watchlist](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### create_watchlist

名前と銘柄を指定して新しいリストを作る。利用例：明示依頼された管理リストを新設する。

既存ラッパー：`TradingViewClient.create_watchlist()` / `CreateWatchlistRequest`。応答：`TypedToolResponse`。主な内容：新規リストのID等を確認し保存。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `name` | 省略可 | string、最大文字数500 | 未記載 |
| `symbols` | 省略可 | 配列<string> / null | 未記載 |

**Write：実行には対象と副作用を含む明示依頼が必要。今回の調査では実行しない。**

根拠：[公式のcreate_watchlist](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### delete_watchlist

IDでリストを削除する。利用例：利用者が対象を明示して削除を依頼した場合。

既存ラッパー：`TradingViewClient.delete_watchlist()` / `DeleteWatchlistRequest`。応答：`TypedToolResponse`。主な内容：削除結果を確認。通常の管理同期はリスト削除を行わない。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `watchlist_id` | 必須 | string | 未記載 |

**Write：実行には対象と副作用を含む明示依頼が必要。今回の調査では実行しない。**

根拠：[公式のdelete_watchlist](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### add_to_watchlist

リストへ銘柄を追加する。利用例：検証済み結果の追加差分を同期する。

既存ラッパー：`TradingViewClient.add_to_watchlist()` / `AddToWatchlistRequest`。応答：`TypedToolResponse`。主な内容：更新結果。既存銘柄の追加は並び順を変え得る。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `watchlist_id` | 必須 | string | 未記載 |
| `symbols` | 必須 | 配列<string> / null | 未記載 |

**Write：実行には対象と副作用を含む明示依頼が必要。今回の調査では実行しない。**

根拠：[公式のadd_to_watchlist](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### remove_from_watchlist

リストから銘柄を除去する。利用例：管理対象の削除差分を同期する。

既存ラッパー：`TradingViewClient.remove_from_watchlist()` / `RemoveFromWatchlistRequest`。応答：`TypedToolResponse`。主な内容：除去結果。誤った空結果を同期しない。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `watchlist_id` | 必須 | string | 未記載 |
| `symbols` | 必須 | 配列<string> / null | 未記載 |

**Write：実行には対象と副作用を含む明示依頼が必要。今回の調査では実行しない。**

根拠：[公式のremove_from_watchlist](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### update_watchlist

リストの名前・説明を変更する。利用例：既知IDの説明文だけを更新する。

既存ラッパー：`TradingViewClient.update_watchlist()` / `UpdateWatchlistRequest`。応答：`TypedToolResponse`。主な内容：更新結果。Providerは名前/説明の少なくとも一方を要求。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `watchlist_id` | 必須 | string | 未記載 |
| `name` | 省略可 | string、最大文字数500 | 未記載 |
| `description` | 省略可 | string / null | 未記載 |

**Write：実行には対象と副作用を含む明示依頼が必要。今回の調査では実行しない。**

根拠：[公式のupdate_watchlist](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

## Market data / OHLCV

### get_ohlcv

指定銘柄の時間足データを取得する。利用例：TSE:7203の日足を30本取得する。

既存ラッパー：`TradingViewClient.get_ohlcv()` / `GetOhlcvRequest`。応答：`ObservedReadResponse`。主な内容：要約と足の時刻・OHLCV。summary=trueでは生の足を省略。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `symbol` | 必須 | string | 未記載 |
| `interval` | 省略可 | string：1m, 5m, 15m, 30m, 1h, 4h, 1D, 1W, M, 1mo, month | 1D |
| `count` | 省略可 | integer、上限5000 | 300 |
| `summary` | 省略可 | boolean | 未記載 |

現行Requestのcount上限は5000。月足はM/1mo/monthを受理する。当日のDiscoveryにある追加引数は後述の差分表を参照。実測の`structured_content`にはトップ階層の`bars`があり、各足は`t,o,h,l,c,v`、tはUTC Unix秒でした。これは当該30本の観測であり、常に同じ内部構造とは決めつけません。

根拠：[公式のget_ohlcv](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

## Economic data

### get_economic_data

経済指標の時系列を取得する。利用例：カタログで確認したGDP指標を期間指定で読む。

既存ラッパー：`TradingViewClient.get_economic_data()` / `GetEconomicDataRequest`。応答：`TypedToolResponse`。主な内容：日付・値と単位/スケール等。固定応答Schemaではない。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `symbol` | 必須 | string | 未記載 |
| `date_from` | 省略可 | string | 未記載 |
| `date_to` | 省略可 | string | 未記載 |

symbolはget_economic_symbolsで確認したECONOMICS:コード。date_from/date_toは日付文字列で、対象期間の提供可否は別に確認する。

根拠：[公式のget_economic_data](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### get_economic_symbols

利用できる経済指標コードを探す。利用例：country=US、category=gdpで候補を調べる。

既存ラッパー：`TradingViewClient.get_economic_symbols()` / `GetEconomicSymbolsRequest`。応答：`ObservedReadResponse`。主な内容：カテゴリ/コード一覧または詳細。指標コードを推測しない。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `country` | 省略可 | string | 未記載 |
| `category` | 省略可 | string：gdp, lbr, prce, hlth, mny, trd, gov, bsnss, cnsm, hse, txs, enrg, clmt | 未記載 |
| `search` | 省略可 | string | 未記載 |

categoryはローカル列挙値。country=国コード、searchは部分検索。

根拠：[公式のget_economic_symbols](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

## Symbol search

### search_symbols

コード・企業名から銘柄を検索する。利用例：query=7203、type_filter=stockで対応付けを調べる。

既存ラッパー：`TradingViewClient.search_symbols()` / `SearchSymbolsRequest`。応答：`ObservedReadResponse`。主な内容：symbol・description・type・exchange等の検索候補。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `query` | 必須 | string | 未記載 |
| `type_filter` | 省略可 | string：stock, etf, bond, forex, index, futures, crypto, all | all |

根拠：[公式のsearch_symbols](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

## Screener

### get_symbol_data

1銘柄の指定列を読む。利用例：TSE:7203のcloseと確認済み指標を読む。

既存ラッパー：`TradingViewClient.get_symbol_data()` / `GetSymbolDataRequest`。応答：`ObservedReadResponse`。主な内容：指定列の値。列の存在とfilter対応は別。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `symbol` | 必須 | string | 未記載 |
| `columns` | 省略可 | 配列<string> / null | name, description, close, change, change_abs, volume, market_cap_basic, price_earnings_ttm, sector, industry |

根拠：[公式のget_symbol_data](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### run_screener

市場・条件・順序・集合で銘柄を抽出する。利用例：日本株PER 0〜15を出来高降順で3件読む。

既存ラッパー：`TradingViewClient.run_screener()` / `RunScreenerRequest`。応答：`ObservedReadResponse`。主な内容：rows・totalCount・ignored_filters等。正規化とcoverageを照合。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `market` | 省略可 | string | america |
| `filters` | 省略可 | object | 未記載 |
| `sort_by` | 省略可 | string | volume |
| `sort_order` | 省略可 | string：asc, desc | desc |
| `limit` | 省略可 | integer、上限1000 | 100 |
| `columns` | 省略可 | 配列<string> / null | 未記載 |
| `symbol_types` | 省略可 | 配列<string> / null | 未記載 |
| `filter_preset` | 省略可 | string：pullback_with_reversal, breakout_with_volume, oversold_healthy, earnings_runup, relative_strength, new_highs | 未記載 |
| `symbolset` | 省略可 | 配列<string> / null | 未記載 |

最大1000行。offset/page/cursorはRequestにない。market=japanと東証プライムは同一ではない。条件名・取得列・Presetは条件カタログを参照。

根拠：[公式のrun_screener](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### get_symbol_data_batch

最大50銘柄の指定列を一括取得する。利用例：既知3銘柄のcloseを一括で照合する。

既存ラッパー：`TradingViewClient.get_symbol_data_batch()` / `GetSymbolDataBatchRequest`。応答：`ObservedReadResponse`。主な内容：取得データ・missing/理由等。部分失敗と未知銘柄を区別。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `symbols` | 必須 | 配列<string>、最大要素数50 / null | 未記載 |
| `columns` | 省略可 | 配列<string> / null | get_symbol_dataと同じ |

symbolsは50要素まで。missing、success=false、partial/warningsを別々に確認する。

根拠：[公式のget_symbol_data_batch](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### get_screener_columns

列・グループ・期間/時間足の候補を探索する。利用例：market=stock、search=RSIで詳細を調べる。

既存ラッパー：`TradingViewClient.get_screener_columns()` / `GetScreenerColumnsRequest`。応答：`ObservedReadResponse`。主な内容：概要の分類/列名、group/search指定時の詳細。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `market` | 省略可 | string：stock, etf, crypto, bond, all | all |
| `group` | 省略可 | string | 未記載 |
| `search` | 省略可 | string | 未記載 |

ここでのmarketはstock/etf/crypto/bond/allで、Screenerのjapan/americaとは異なる。全体概要の後にgroup/searchで絞る。

根拠：[公式のget_screener_columns](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### get_technicals_rating

1銘柄・単一時間足のテクニカル評価を読む。利用例：TSE:7203の1Dと1hの評価を別々に読む。

既存ラッパー：`TradingViewClient.get_technicals_rating()` / `GetTechnicalsRatingRequest`。応答：`ObservedReadResponse`。主な内容：RSI等の指標と総合/MA/その他評価。期間の一致を実応答で確認。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `symbol` | 必須 | string | 未記載 |
| `interval` | 省略可 | string：1m, 5m, 15m, 30m, 1h, 2h, 4h, 1D, 1W, 1M | 1D |

OHLCVと許容intervalが異なる（2hと月足表記など）。RSI14やSMA25の存在・意味をTool名だけで保証しない。

根拠：[公式のget_technicals_rating](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

## News

### get_news

銘柄ニュースの見出しを読む。利用例：既知銘柄の日本語ニュースを3件読む。

既存ラッパー：`TradingViewClient.get_news()` / `GetNewsRequest`。応答：`TypedToolResponse`。主な内容：見出し・id・時刻・配信元・権利/有料区分等、ページング情報。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `symbol` | 必須 | string | 未記載 |
| `lang` | 省略可 | string：言語コードL（末尾） | en |
| `limit` | 省略可 | integer、上限200 | 25 |
| `offset` | 省略可 | integer | 未記載 |

limit上限200、公開説明の取得範囲は合計最大200見出し。offsetの継続は応答のhas_more/total_available等で判断し、Screenerにこのページングを流用しない。

根拠：[公式のget_news](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### get_news_story

取得済みニュースIDで記事を読む。利用例：get_newsのidをそのまま渡す。

既存ラッパー：`TradingViewClient.get_news_story()` / `GetNewsStoryRequest`。応答：`TypedToolResponse`。主な内容：記事本文/要約等。権利・利用可能範囲を確認。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `id` | 必須 | string | 未記載 |
| `lang` | 省略可 | string | en |
| `user_prostatus` | 省略可 | string：pro, non_pro | non_pro |
| `user_country` | 省略可 | string | 未記載 |

langは任意文字列。user_prostatus/user_countryは表示条件で、契約プランの権限を上書きする引数ではない。

根拠：[公式のget_news_story](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

## Fundamentals & forecasts

### get_forecasts

アナリスト予想を読む。利用例：既知銘柄の目標株価と予想利益を確認する。

既存ラッパー：`TradingViewClient.get_forecasts()` / `GetForecastsRequest`。応答：`TypedToolResponse`。主な内容：評価分布・目標・予想等。列挙や入れ子は実応答で確認。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `symbol` | 必須 | string | 未記載 |

根拠：[公式のget_forecasts](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### get_financials

指定期間の財務指標を読む。利用例：period=ttmでPERや利益率を確認する。

既存ラッパー：`TradingViewClient.get_financials()` / `GetFinancialsRequest`。応答：`TypedToolResponse`。主な内容：財務スナップショット。通貨・単位・期間を確認。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `symbol` | 必須 | string | 未記載 |
| `metric` | 省略可 | 配列<string> / null | 未記載 |
| `period` | 省略可 | string：fy, fq, ttm, fh, current | ttm |

根拠：[公式のget_financials](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### get_financial_history

決算指標の履歴を読む。利用例：period=fqで四半期の売上推移を調べる。

既存ラッパー：`TradingViewClient.get_financial_history()` / `GetFinancialHistoryRequest`。応答：`TypedToolResponse`。主な内容：期間ラベル・財務値・増減率等。株価の足とは別。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `symbol` | 必須 | string | 未記載 |
| `period` | 省略可 | string：fq, fy | fq |
| `date_from` | 省略可 | string | 未記載 |
| `date_to` | 省略可 | string | 未記載 |

根拠：[公式のget_financial_history](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

## Documents

### get_documents

銘柄の開示文書・イベント文書を探す。利用例：決算資料の候補を期間/カテゴリで絞る。

既存ラッパー：`TradingViewClient.get_documents()` / `GetDocumentsRequest`。応答：`TypedToolResponse`。主な内容：文書メタデータとviews等。view_idを応答から取得。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `symbol` | 必須 | string | 未記載 |
| `category` | 省略可 | string：all, annual_reports, quarterly_reports, interim_reports, company_events, insider_transactions, transcripts, presentations, press_releases, other, 10-K, 10-Q, 8-K | 未記載 |
| `event` | 省略可 | string：earning, corporate_event | 未記載 |
| `start_date` | 省略可 | string | 未記載 |
| `end_date` | 省略可 | string | 未記載 |
| `limit` | 省略可 | integer | 20 |

limitはRequestに上限なし、Provider上限は今回未確認。start_date/end_dateはRFC3339のイベント日範囲であり、文書取得日と混同しない。

根拠：[公式のget_documents](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### get_document_view

取得済みview_idで文書ビューを読む。利用例：get_documentsのviewsのidをそのまま渡す。

既存ラッパー：`TradingViewClient.get_document_view()` / `GetDocumentViewRequest`。応答：`TypedToolResponse`。主な内容：文書ビューの本文/要約等。IDを合成しない。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `view_id` | 必須 | string | 未記載 |

根拠：[公式のget_document_view](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

## Calendars

### get_earnings_calendar

銘柄群の直近・次回決算予定を読む。利用例：既知3銘柄の次回決算日を確認する。

既存ラッパー：`TradingViewClient.get_earnings_calendar()` / `GetEarningsCalendarRequest`。応答：`TypedToolResponse`。主な内容：次回予定と直近報告。過去全履歴ではない。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `symbols` | 必須 | 配列<string> / null | 未記載 |
| `date_from` | 省略可 | string | today |
| `date_to` | 省略可 | string | +180d |

日付はYYYY-MM-DDまたはRFC3339。日付範囲を広げても全決算履歴にならない。履歴はget_financial_historyや文書で検討する。

根拠：[公式のget_earnings_calendar](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### get_economic_calendar

国・通貨等で経済イベントを読む。利用例：US/USDの重要イベントを日付指定で読む。

既存ラッパー：`TradingViewClient.get_economic_calendar()` / `GetEconomicCalendarRequest`。応答：`TypedToolResponse`。主な内容：イベント日時・重要度・予想/実績等。提供範囲を確認。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `countries` | 省略可 | string | US |
| `currencies` | 省略可 | string | 未記載 |
| `category` | 省略可 | string：gdp, bonds, business, consumer, goverment, health, housing, labor, money, prices, trade, taxes, all | 未記載 |
| `date_from` | 省略可 | string | today 00:00 UTC |
| `date_to` | 省略可 | string | today 23:59 UTC |
| `min_importance` | 省略可 | integer、上限1、下限-1 / null | -1 |

カテゴリの綴りgovermentはSchema/公式表記に従う。公開説明の過去範囲は2003-09-01以降、将来は約31日先までで、実機では未検証。

根拠：[公式のget_economic_calendar](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### get_dividends_calendar

銘柄または市場の配当日程を読む。利用例：既知銘柄の配当落ち日を確認する。

既存ラッパー：`TradingViewClient.get_dividends_calendar()` / `GetDividendsCalendarRequest`。応答：`TypedToolResponse`。主な内容：権利日・支払日・配当/利回り等。市場モードは上限あり。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `symbols` | 省略可 | 配列<string> / null | 未記載 |
| `market` | 省略可 | string | 未記載 |
| `date_from` | 省略可 | string | now |
| `date_to` | 省略可 | string | +30d |
| `limit` | 省略可 | integer、上限200 | 50 |

銘柄モードsymbolsと市場モードmarketを区別する。市場モードのlimit上限200。

根拠：[公式のget_dividends_calendar](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

## Alerts

### create_alert

単純な価格条件のAlertを作る。利用例：明示依頼された価格上抜け通知を作る。

既存ラッパー：`TradingViewClient.create_alert()` / `CreateAlertRequest`。応答：`TypedToolResponse`。主な内容：alert_id・starting等。作成後の有効状態を別途読む。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `symbol` | 必須 | string | 未記載 |
| `price` | 省略可 | number | 未記載 |
| `condition` | 省略可 | string：cross, cross_up, cross_down, greater, less | cross |
| `message` | 省略可 | string、最大文字数4000 | 未記載 |
| `name` | 省略可 | string、最大文字数300 | 未記載 |
| `resolution` | 省略可 | string | 1 |
| `expiration` | 省略可 | string | now+30d |
| `auto_deactivate` | 省略可 | boolean | false |
| `email` | 省略可 | boolean | false |
| `mobile_push` | 省略可 | boolean / null | true |
| `popup` | 省略可 | boolean / null | true |
| `conditions` | 省略可 | 配列<object> / null | 未記載 |

価格の単一条件のみが現行公式説明の対象。多条件・指標条件・webhook付き作成はProvider制限あり。conditionsや追加webhook/monitorをRequestが受理しても利用可能とは保証しない。

**Write：実行には対象と副作用を含む明示依頼が必要。今回の調査では実行しない。**

根拠：[公式のcreate_alert](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### update_alert

Alertの通知設定等を変更する。利用例：既知alert_idの通知方法だけを変更する。

既存ラッパー：`TradingViewClient.update_alert()` / `UpdateAlertRequest`。応答：`TypedToolResponse`。主な内容：更新結果。変更後の状態を読む。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `alert_id` | 必須 | integer | 未記載 |
| `message` | 省略可 | string / null | 未記載 |
| `name` | 省略可 | string / null | 未記載 |
| `expiration` | 省略可 | string / null | 未記載 |
| `auto_deactivate` | 省略可 | boolean / null | 未記載 |
| `email` | 省略可 | boolean / null | 未記載 |
| `mobile_push` | 省略可 | boolean / null | 未記載 |
| `popup` | 省略可 | boolean / null | 未記載 |

symbol/condition/timeframeは変更対象外。webhook付き更新は制限あり。expiration空文字による解除はプラン依存。Requestの追加webhook許可をProvider対応と取り違えない。

**Write：実行には対象と副作用を含む明示依頼が必要。今回の調査では実行しない。**

根拠：[公式のupdate_alert](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### delete_alert

ID群のAlertを削除する。利用例：利用者が指定したAlertを削除する。

既存ラッパー：`TradingViewClient.delete_alert()` / `DeleteAlertRequest`。応答：`TypedToolResponse`。主な内容：削除結果。発火履歴も削除され得る。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `alert_ids` | 必須 | 配列<integer> / null | 未記載 |

**Write：実行には対象と副作用を含む明示依頼が必要。今回の調査では実行しない。**

根拠：[公式のdelete_alert](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### stop_alerts

Alertを停止する。利用例：明示依頼されたAlertを一時停止する。

既存ラッパー：`TradingViewClient.stop_alerts()` / `StopAlertsRequest`。応答：`TypedToolResponse`。主な内容：停止結果。削除とは異なり履歴/設定を保持。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `alert_ids` | 必須 | 配列<integer> / null | 未記載 |

**Write：実行には対象と副作用を含む明示依頼が必要。今回の調査では実行しない。**

根拠：[公式のstop_alerts](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### restart_alerts

停止中のAlertを再開する。利用例：利用者が指定したAlertを再開する。

既存ラッパー：`TradingViewClient.restart_alerts()` / `RestartAlertsRequest`。応答：`TypedToolResponse`。主な内容：再開結果。最終状態を確認。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `alert_ids` | 必須 | 配列<integer> / null | 未記載 |

**Write：実行には対象と副作用を含む明示依頼が必要。今回の調査では実行しない。**

根拠：[公式のrestart_alerts](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### list_alerts

Alert一覧を条件付きで読む。利用例：既知銘柄のactiveなAlertを一覧する。

既存ラッパー：`TradingViewClient.list_alerts()` / `ListAlertsRequest`。応答：`TypedToolResponse`。主な内容：alert_id・symbol・active・条件・閾値・時刻等の正規化項目。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `symbol` | 省略可 | string | 未記載 |
| `active` | 省略可 | boolean / null | 未記載 |

根拠：[公式のlist_alerts](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### get_alerts

指定Alertの詳細を読む。利用例：設定変更を検討する前に既知IDの条件を確認する。

既存ラッパー：`TradingViewClient.get_alerts()` / `GetAlertsRequest`。応答：`TypedToolResponse`。主な内容：詳細条件等。message/webhook URLは除去されhas_webhook等を返す場合あり。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `alert_ids` | 必須 | 配列<integer> / null | 未記載 |

根拠：[公式のget_alerts](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### get_alerts_log

発火履歴を条件付きで読む。利用例：直近7日の既知銘柄の発火を3件確認する。

既存ラッパー：`TradingViewClient.get_alerts_log()` / `GetAlertsLogRequest`。応答：`TypedToolResponse`。主な内容：発火時刻・symbol・message・配信状況等。個人情報を扱う。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `days` | 省略可 | integer | 7 |
| `symbol` | 省略可 | string | 未記載 |
| `limit` | 省略可 | integer、上限2000 | 100 |

limit上限2000。取得したmessageや配信状態に個人情報が含まれ得る。

根拠：[公式のget_alerts_log](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

## 銘柄・市場・時間足・言語

- 銘柄は`EXCHANGE:TICKER`（例`TSE:7203`）。search_symbolsで候補を読み、検索一致だけで企業/上場区分を確定しない。母集団と上位N件、指数と市場区分は別です。
- Screenerの市場例は`japan`・`america`等。全市場の固定enumはRequestにありません。列探索のmarketは`stock`等の種別であり別名前空間です。指数はindex分類やsymbolsetで指定し、東証プライムの未確認filterを創作しません。
- OHLCVとtechnicalsのintervalは各表の許容値に従います。日足`1D`と1時間足`1h`、月足表記の差を保ち、指標期間・確定足・基準時刻を別途確認します。
- 言語コードL（GetNewsRequest）は`en, ru, de, fr, es, pt, it, pl, tr, ar, he, ko, ja, vi, th, ms, id, zh-Hans, zh-Hant, ro, en_IN`。GetNewsStoryRequestのlangは現行Schemaでは任意stringです。

## Screening・指標・複合処理の使い分け

対応する単一条件は[標準JSON](SCREENING_MANUAL.md)が第一候補です。条件名・取得列・Presetの違いは[条件カタログ](SCREENER_CONDITIONS.md)を使い、直接取得→既存ラッパーの組合せ→母集団が確定できない場合だけ外部一覧の順に調べます。

既存指標はget_symbol_data/batchやget_technicals_ratingで調べ、期間・足が合えば再計算を避けます。SMA25等が直接取れなければget_ohlcvによるローカルPython計算も選択肢です。NaN/欠損・25確定日足・時系列・重複・日時・価格調整を検証し、部分結果を全件成功としません。

財務履歴、経済時系列、ニュース、文書、各カレンダーは用途の異なるReadです。取得可能な過去/将来期間、通貨・単位、公開/更新時点、利用権限を確認し、任意応答を標準Screening履歴対応と説明しません。

### 既存ラッパーを呼ぶRead例

これは既存認証を利用して1銘柄を読む例です。ファイルの作成/実行が依頼された時だけ、実際の保存先・環境・起動コマンド・結果保存先を提示して実行します。以下の関数定義だけではデータ取得や結果保存は行いません。

```python
from tradingview_screening.integrations.tradingview.client import TradingViewClient
from tradingview_screening.integrations.tradingview.schemas import GetSymbolDataRequest

async def read_one():
    async with TradingViewClient() as client:
        return await client.get_symbol_data(
            GetSymbolDataRequest(symbol="TSE:7203", columns=["close"])
        )
```

Windowsのコマンドプロンプトではリポジトリルートで`call scripts\setenv.bat`後の`"%PYTHON_EXECUTABLE%"`を使います。通常Screeningは`app.bat screen <name>`で実行します。独自Pythonをscreen/Jobへ渡さず、[AIガイドの起動・実行契約](AI_JSON_GUIDE.md#作成して実行の完了契約)に従います。

## Provider制限・プラン・安全性

全Toolにインターネット・公式MCP対象プラン・保存済み認証・Tool権限が必要です。公開資料ではEssential以上/試用プラン除外と案内されていますが、契約条件は公式ページで再確認してください。これはAIへの別途サーバー登録を求める意味ではありません。

Providerの目安は約100要求/分、アプリ既定Governorは30要求/分・同時1・試行Timeout30秒・最大3試行です。接続/OAuth段階の待ち時間は別で、実行全体が30秒以内とは限りません。Writeは自動Retry/cache対象外。Readも既存Governorを経由し、検証のために無制限の並列/全銘柄取得をしません。

無条件全米株Screenerの拒否と最大1000行は[現行の制約](SCREENING_MANUAL.md#公式mcp-beta版のスクリーニング制限2026-10-18実機確認)。他のラッパーで同じ母集団を確定できるかは別調査で、S&P 500へ勝手に縮小しません。Watchlist/Alertの個人情報や生応答・tokenをチャット/commitへ載せません。

## 公式資料・実装・Discoveryの差分

| 項目 | 照合結果と扱い |
| --- | --- |
| Tool集合 | 公開資料・ローカル・当日Discoveryの35名が一致。不足/追加は0。全Toolの実行成功を示すものではない |
| get_ohlcvの追加引数 | 当日Discoveryにはdate_from/date_to/formatがあるが、公開ページは未掲載、現行Requestはsymbol/interval/count/summaryのみ。追加引数は既存ラッパーで未対応。独自通信で回避せず、必要なら別の実装課題とする |
| update_watchlist.description | 公開ページと現行Requestにはあるが、当日Discoveryにはない。Writeを実行しての可否検証はしていない |
| Alert追加キー | ローカルCreateはwebhook/monitor、Updateはwebhookを受理し得るが、公開ページはwebhook等を制限。Schema適合を実行成功としない |
| NULL・型・上限 | ローカルには必須nullableや公開資料で未指定の上限がある。表はローカル契約、意味的な成功はProvider側で別途確認 |
| 応答 | Read包絡の型検証はあるが、全35 Toolの完全な出力Schema/全キーは固定していない。公開説明と実応答を混同しない |

## 確認状態と仕様変更への対応

2026-10-26 23:12〜23:16 JST、Windows Embedded Python 3.12.8・既存Client/認証/Governorで接続とDiscoveryを確認しました。Discoveryを除く個別Readは**6 Tool・16呼出し**です。14回のsuccess応答と、SMA/prime検索の「一致列なし」2回を記録しました。success応答のうちfilterキー2種類は無視されており、条件成功には数えません。

| 個別実行Tool | 当日の確認状態 |
| --- | --- |
| get_screener_columns | stock概要17分類163列、valuation/technicals詳細、SMA/EMA/prime検索の計6回 |
| run_screener | Japan各3件の5filter試験（適合3・無視2）、americaのpreset 1種類3件。計6回。全件網羅・preset全内部式は未検証 |
| get_symbol_data | TSE:7203の5列、1h RSI派生列を含む数値取得。期間14との同一性・filterは未検証 |
| get_symbol_data_batch | 既知2銘柄の3列、取得2・missing 0。未知/部分失敗の回復試験は未実施 |
| get_technicals_rating | TSE:7203の日足snapshot。SMA20/50等の応答項目あり、SMA25は当該応答にない |
| get_ohlcv | TSE:7203の日足30本、summary=falseの足構造を確認。全銘柄/価格調整/完全なSMA25抽出は未検証 |
| 上記以外の29 Tool | 公開資料・ローカル契約・Discoveryのみ照合し、個別実行は未実施。Write10 Toolとget_active_watchlistは副作用を避けて除外 |

filterの実値検証・無視されたキーは[条件カタログ](SCREENER_CONDITIONS.md#filter適用を確かめる手順)に記載しています。初回のsandbox内statusは接続待ちで中断し、ネットワーク利用可能な実行でstatus成功を確認しました。認証設定や資格情報の手動変更は行っていません。

Beta更新時は公式ページのTool集合と既存TOOL_NAME_MAP/REQUEST_MODELSを比較し、既存Client.list_tools()の名前・inputSchema・不足/追加を照合します。列探索は概要→必要なgroup/search、filterは少数取得でignored_filters・実値・単位・件数を検証します。差分を記録し、型やCLIの拡張が必要なら別のdevelop向け実装として扱います。公式説明や生schemaの長文保存物をそのまま配布しません。

技術契約は[既存Client](../../src/tradingview_screening/integrations/tradingview/client.py)・[Request/Response](../../src/tradingview_screening/integrations/tradingview/schemas.py)・[Governor](../../src/tradingview_screening/common/request_governor.py)、開発向け解説は[developのAPI資料](https://github.com/TakamKaji/tradingview_mcp_support/blob/develop/docs/development/API.md)を参照します。

[条件カタログ](SCREENER_CONDITIONS.md) / [利用者マニュアル](README.md)
