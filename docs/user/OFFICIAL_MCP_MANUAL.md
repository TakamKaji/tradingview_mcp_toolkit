# 公式MCP機能マニュアル

調査基準日：**2026-10-27 JST（OHLCV契約更新）**。全Toolの初回調査は2026-10-26、基点developは`0a8cf09`。PR #63の文書をdevelopへマージした`0095ee9`と、PR #65の実装を統合して更新しています。[公式MCP資料](https://www.tradingview.com/mcp/docs)と既存Client/Request/Responseを照合した利用者向け機能解説の正本です。公式ページの転載ではなく、本リポジトリでの使い分けを説明します。

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

全メソッドは非同期です。`TypedToolResponse`は`structured_content`と`content`を分離します。`ObservedReadResponse`はその内側のsuccess/error/count/missing_count等を型検証し、Tool別の追加データを保持します。これは足/記事/銘柄の完全固定Schemaではありません。2026-10-27の公式MCP**直接実行**では18 Read Tool・40回中、Providerの`success:true`が31回、`success`キーなし9回（うち経済カレンダー3回は`status:ok`）でした。Toolごとに成功の表現が異なり、`success`欠落だけを失敗と決めません。反対に`success:true`でも`ignored_filters`・`missing`・各列のnull・取得範囲を検査します。型付き包絡を配列として扱わず、実応答・success/partial/missing・単位/日時/欠損を確認してください。下記の「主な内容」は用途の説明で、全キーの存在保証ではありません。

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
| `count` | 省略可 | integer、上限8000。ただしrows/format省略時は5000 | 300 |
| `date_from` | 省略可 | string：有効なYYYY-MM-DDまたは時差付きRFC3339 | 公開ページ未掲載、既定は未確認 |
| `date_to` | 省略可 | string：有効なYYYY-MM-DDまたは時差付きRFC3339 | 公開ページ未掲載、既定は未確認 |
| `format` | 省略可 | string：rows, columns | 公開ページ未掲載、Discovery説明ではrows |
| `summary` | 省略可 | boolean | 未記載 |

日付の両端を含む範囲を指定でき、範囲内の新しい足からcount本まで取得します。日時文字列は変換せず送信します。新3引数は未指定なら送信せず従来動作を維持し、明示null、不正日付/時刻/時差、未知formatは拒否します。月足はM/1mo/monthを受理します。公開ページとDiscoveryの差は後述の差分表を参照してください。

生の足を使う場合は`summary=False`を指定します。実測では`structured_content`直下の`bars`が、rowsでは`t,o,h,l,c,v`を持つ足ごとの辞書配列、columnsでは`t/o/h/l/c/v`それぞれの配列を持つ辞書でした。tはUTC Unix秒です。`ObservedReadResponse.structured_content`はモデルなので、辞書で扱う場合は`response.model_dump(mode="json")["structured_content"]`を使います。`has_more`・`next_date_to`等は追加応答項目として保持されますが、自動ページングはしません。遡る場合は返却されたnext_date_toを使い、重複・欠損・対象日時・完全性を検証します。

2026-10-27の少量Readで、日付/RFC3339・**限定した短い期間の**rows/columns全OHLCV値の一致・カーソル遡り・旧引数の互換を確認しました。**第4ラウンドの長い系列・特定日付窓では形式による値差も再現**されており、rows/columnsの同一性を一般保証しません。columnsのcount=5001/8000指定は5営業日windowで受理され、実取得は5本です。**8000本全件の取得成功を意味しません。** 巨大応答、全期間、価格調整、確定足の完全性は未確認です。別セッションの直接MCP Readでは`count=9000,summary=true`を短い18本窓に指定しても拒否されませんでしたが、実取得上限の突破は示しません。返却noticeは形成中足の可能性、通常取引時間、株式分割調整について注意喚起しており、確定足フラグの存在は未確認です。第2ラウンドの公式MCP直接Readでは、同じ5本のrows/columns全OHLCVが一致し、Apple日足と1h/4hの同取引日最終closeに343.91/343.99の差がありました。350本から算出した日足RSI7/SMA13/EMA13は直接列と一致した一方、日中足のRSI/EMA/MACDには差が残りました。**続く第4ラウンドではToyotaの日中足の差は過去バーの形式別値差で数値上説明でき、Appleの日中足では未解決のまま**です。さらに`count=9000,summary=true`ではAppleの日足6,744本を**集計**できましたが、生バーを6,744本取得したわけではなく、rows5000/columns8000の生データ上限は未検証です。

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

10/27の公式MCP直接Readでは、米国金利・インフレ・失業率が2026年1〜9月の月次9点を返し、`unit:%/scale:100`でも`value`は4.0等の百分率表示値でした。`scale`を無条件に乗算せず、公表時刻・改定値・提供遅延を別に扱います。

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

第3ラウンドの公式MCP直接Readでは、`search_symbols`が返した先物rootが`get_symbol_data_batch`ではmissingになる例がありました。検索はfuzzy候補の発見であり、価格Read可能な識別子の保証ではありません。先物は`run_screener`のmarket/exchangeとtype/subtype/descriptionから連続・限月識別子を発見し、その**返却された正確なシンボル**で少量Readを検証します。金先物・原油先物ではrootから連続・標準/Microなど商品が変わるため、自動的な別名変換をしません。米10年利回りは`type_filter:index`検索で見つからず、型指定なしで`TVC:US10Y`（`type:bond`）を確認しました。

根拠：[公式のsearch_symbols](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

## Screener

### get_symbol_data

1銘柄の指定列を読む。利用例：TSE:7203のcloseと確認済み指標を読む。

既存ラッパー：`TradingViewClient.get_symbol_data()` / `GetSymbolDataRequest`。応答：`ObservedReadResponse`。主な内容：指定列の値。列の存在とfilter対応は別。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `symbol` | 必須 | string | 未記載 |
| `columns` | 省略可 | 配列<string> / null | name, description, close, change, change_abs, volume, market_cap_basic, price_earnings_ttm, sector, industry |

10/27第2ラウンドの**公式MCP直接観測**では`RSI7/9/21`、`SMA13/21`、`EMA13/21`等が数値を返した一方、`RSI14/24/48/96/192`、`SMA48/96/192`、`EMA48/96/192`は指定した日米2銘柄でnullでした。既定`RSI`は14期間Wilder計算と近似一致しても**明示`RSI14`はnull**で、任意整数期間の取得を保証しません。列名の大小文字も個別確認が必要です（例：`RSI7`は数値、`rsi7`はnull）。詳細は[条件カタログ](SCREENER_CONDITIONS.md)。

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

最大1000行。offset/page/cursorはRequestにない。market=japanと東証プライムは同一ではない。10/27第2ラウンドの**公式MCP直接観測**では、日経225 symbolsetで`RSI7:[80,100]`が225→3件、`MACD.macd:[0,1]`が225→1件、`MACD.signal:[0,1]`が225→2件となり、取得全行が条件に適合しました。対して`RSI|60`・`RSI7|240`・`SMA96`・`EMA96`は`ignored_filters`に入りました。**単体Readで取得できる列でもfilterに利用可能とは限りません**。第3ラウンドの公式MCP直接Readでは、S&P 500の`symbolset:["SYML:SP;SPX"]`でstock 503/503行、NASDAQ 100のindex filterで型省略101/101行、stock限定98/98行、日経225の`symbolset:["SYML:TVC;NI225"]`でstock 225/225行を取得（重複0）しました。NASDAQ 100の差3行は`type:"dr"`のARM/ASML/PDDで、**指数全構成員の依頼に`symbol_types:["stock"]`を安易に追加すると欠落**します。`filters.index:"nikkei 225"`は成功0行、`filters.index:"TOPIX"`は明示拒否でした。全返却はProviderが定義する集合の完全取得であり、指数算出元との独立の網羅性保証ではありません。条件名・取得列・Presetは条件カタログを参照。

根拠：[公式のrun_screener](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### get_symbol_data_batch

最大50銘柄の指定列を一括取得する。利用例：既知3銘柄のcloseを一括で照合する。

既存ラッパー：`TradingViewClient.get_symbol_data_batch()` / `GetSymbolDataBatchRequest`。応答：`ObservedReadResponse`。主な内容：取得データ・missing/理由等。部分失敗と未知銘柄を区別。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `symbols` | 必須 | 配列<string>、最大要素数50 / null | 未記載 |
| `columns` | 省略可 | 配列<string> / null | get_symbol_dataと同じ |

symbolsは50要素まで。missing、success=false、partial/warningsを別々に確認する。10/27の公式MCP直接観測では重複と無効銘柄を混ぜた4入力から有効2件、`missing_count:1`を`success:true`かつ`partial`キーなしで返したため、`success:true`を全銘柄成功と扱いません。

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

langは任意文字列。user_prostatus/user_countryは表示条件で、契約プランの権限を上書きする引数ではない。別セッションの直接MCP Readでは日米記事2件とも`success`キーなしで、`ast_description`はJSON文字列でした。`get_news`で得た非URN形式のIDも無加工で受理され、`permission:headline`でもAST本文が返る1例がありましたが、閲覧・再配布権や全記事対応を意味しません。

根拠：[公式のget_news_story](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

## Fundamentals & forecasts

### get_forecasts

アナリスト予想を読む。利用例：既知銘柄の目標株価と予想利益を確認する。

既存ラッパー：`TradingViewClient.get_forecasts()` / `GetForecastsRequest`。応答：`TypedToolResponse`。主な内容：評価分布・目標・予想等。列挙や入れ子は実応答で確認。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `symbol` | 必須 | string | 未記載 |

2026-10-27の**公式MCP直接観測（第2・第5ラウンド）**では、トヨタ・ソニーに加え、三菱UFJ（8306）・日立（6501）でもraw予想EPS/売上と`get_forecasts`の比率が期間別に同一でした（次FQ `157.4059499449`倍、次FY `158.7805652588`倍、基本EPS TTM `162.6280696048`倍）。価格・財務・forecast表示通貨はJPYですが、予想対象期末・換算元通貨・適用レートは取得できず、**変換の原因は未確定**です。AppleとTSM ADRでは数値のある次FQ/FY予想がrawと一致しましたが、検証対象の全海外銘柄への一般化はできません。4日本株の`get_forecasts`は`success:true`でも`target_mismatch:true`で目標株価がnullとなり、raw目標の値が存在することは品質ガードを迂回してよい根拠ではありません。`quality_note`・通貨・単位・期間を検証できるまで、これらの予想を自動換算したり予想PER/成長率/目標株価へ結合したりしません。**画面との追加照合（ユーザーによる2026-10-27の確認）**：日立製作所のTradingView画面にEPS **176.99 JPY**と表示され、公式MCPのraw列`earnings_per_share_basic_ttm=176.9908`を小数2位へ丸めた値と一致。対照の`get_forecasts.estimates.eps_ttm=1.0883164292`とは約162.628倍異なります。**画面のEPS表示対象期間・基本/希薄化のUIラベルは未照合**ですが、この数値一致は少なくともraw TTM値の表示整合性を支持します。全日本株のraw値の正確性まで保証しません。 **為替変換モデルの直接検証（公式MCP Read、2026-10-27 22:16〜22:18 JST）：** 上述の各社に見られた倍率差は、公式MCPで実取得した`FX_IDC:JPYUSD`の日足終値との**数値的な完全一致**が追加確認されました。全4社×5項目で`get_forecasts値 = raw値 × JPYUSD終値`がPython floatの厳密比較（==）で20/20件成立し、最大誤差0。係数は次FQ（2026-09-30候補日）`0.006353`、次FY（2026-03-31候補日）`0.006298`、EPS TTM（2026-06-30候補日）`0.006149`。直接`FX:USDJPY`または`FX_IDC:USDJPY`のOHLCには厳密一致せず、**逆通貨ペアの実取得終値**が一致しました。JPYラベル付きforecastがUSD換算相当の数値となることを強く支持しますが、**MCP内部でのペア選択・換算実行箇所・会計期間の基準日選択は未証明**です。前回の外部USDJPY履歴との近似に比べ、今回は逆通貨ペアの係数を直接再現できています。次FYの2026-03-31は4社の直近実績FY末ですが、次FY予想の基準日になる仕組みは不明。固定係数の適用や品質ガードの迂回は行いません。公式通貨変換の背景は[TradingView株式Screenerの通貨変換説明](https://www.tradingview.com/support/solutions/43000639101-currency-conversion-in-the-stock-screener/)、実測詳細は下記「JPYUSD終値と日本株forecastの20件一致」を参照。

根拠：[公式のget_forecasts](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### get_financials

指定期間の財務指標を読む。利用例：period=ttmでPERや利益率を確認する。

既存ラッパー：`TradingViewClient.get_financials()` / `GetFinancialsRequest`。応答：`TypedToolResponse`。主な内容：財務スナップショット。通貨・単位・期間を確認。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `symbol` | 必須 | string | 未記載 |
| `metric` | 省略可 | 配列<string> / null | 未記載 |
| `period` | 省略可 | string：fy, fq, ttm, fh, current | ttm |

2026-10-27の公式MCP直接観測では、`metric:[revenue,eps,net_income]`は`period:fq/fy`に応じた列を返しましたが、`period:fy`でも`pe`は`price_earnings_ttm`でした。さらにトヨタ/Appleの`period:ttm`で裸列`net_income`は**FYと同値、`net_income_ttm`とは別値**でした。裸の`oper_income`はnullで、明示`oper_income_ttm`を指定しても`period:fq/fy`で返却列が期間に置換される例があります。`eps` aliasは基本EPSへ写像される一方、`get_financial_history`のApple EPSは希薄化後に一致しました。固定期間で数値比較する場合は`get_symbol_data_batch`の明示列と照合し、返却列名のsuffix・定義を確認してください。未知metricやnullを一律ゼロとしません。

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

2026-10-27の公式MCP直接観測では、日米2銘柄のFQ履歴が7系列を返しましたが、説明にある営業利益系列は今回の応答に含まれませんでした。第2ラウンドではFQの2020〜2021年指定は両銘柄とも`success:false`で履歴なし、2020〜2024年指定では**Q3 2022〜Q4 2024の10期**が返り、FYは2020〜2025年の6期を取得できました。返却数を固定の上限と断定しません。トヨタの履歴`Q2 2026`と、同額売上を持つ文書の`FY2027 Q1`は表記が異なります。さらに年次文書要約の純利益「増加」と、財務履歴の前年同期比約-19.2%が矛盾しました。**文書要約や履歴ラベルを無検証で正本にせず**、返却値・期末日・原文書を突き合わせます。

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

limitはRequestに上限なし、Provider上限は今回未確認。start_date/end_dateはRFC3339のイベント日範囲であり、文書取得日と混同しない。別セッションでは日米各2件の文書メタデータ・view候補を取得しましたが、日本の`interim_report`を決算短信や有価証券報告書原本と同定していません。

根拠：[公式のget_documents](https://www.tradingview.com/mcp/docs) / [現行Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。動作確認：静的照合、今回の個別実行は末尾参照。

### get_document_view

取得済みview_idで文書ビューを読む。利用例：get_documentsのviewsのidをそのまま渡す。

既存ラッパー：`TradingViewClient.get_document_view()` / `GetDocumentViewRequest`。応答：`TypedToolResponse`。主な内容：文書ビューの本文/要約等。IDを合成しない。

| 引数 | 必須性 | 型・許容値・ローカル上限 | 公式既定 |
| --- | --- | --- | --- |
| `view_id` | 必須 | string | 未記載 |

2026-10-27の公式MCP直接観測では、`get_document_view`の`astDescription`はオブジェクトで、`get_news_story`のJSON文字列型ASTとは異なりました。返却`id`は入力したsummaryの`view_id`ではなく原文書IDでした。解析時はTool別に型を確認し、両IDを区別して保持します。

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

日付はYYYY-MM-DDまたはRFC3339。日付範囲を広げても全決算履歴にならない。履歴はget_financial_historyや文書で検討する。10/27の直接MCP ReadではAppleの次回予定を返しましたが、トヨタは0件でした。第2ラウンドではトヨタ/ソニー/三菱UFJの2026〜2027年の広い窓でも0件なのに、同日の`get_symbol_data_batch`でトヨタ/ソニーの次回決算予定が窓内で取得できました。第5ラウンドでは2026-10-01〜12-31窓の3銘柄一括指定で、raw次回日時が11/5のトヨタ・11/10のソニーは**返却なし**、11/2のAppleだけ返却され`next_date_confirmed:true`でした。市場・Toolごとの取得経路差や欠損原因は未確定です。**0件を無発表・予定なし・通知不要と断定しない**でください。raw次回日時も独立した会社発表で確定したものとは扱いません。指定窓外の直近報告日が同一行に併記され得る点にも注意します。

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

カテゴリの綴りgovermentはSchema/公式表記に従う。公開説明の過去範囲は2003-09-01以降、将来は約31日先までで、厳密な境界は未検証。10/27の直接MCP Readでは過去・近未来のイベントを`status:ok`（`success`キーなし）で返しました。`actual/actualRaw`と`unit/scale`は別表現であり、先物や経済統計の数値を無条件に倍率変換しません。

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

銘柄モードsymbolsと市場モードmarketを区別する。市場モードのlimit上限200。2026-10-27の公式MCP直接Readでは`symbols:[TSE:7203,NASDAQ:AAPL]`と2025年の日付窓を指定しても、Appleの2026年の直近配当情報が返りました。**銘柄モードで指定日付に制限された履歴を取得できたとは扱いません**。トヨタ0件を無配や日本株非対応とは断定しません。第2ラウンドではソニー/三菱UFJもsymbolsモード0件でしたが、`market:japan`かつ2026年9月の権利落ち日範囲では3件を取得し、全3件の**recent権利落ち日**が指定窓内でした。第5ラウンドではmarketで確認したその同じ3銘柄（3659/6191/8708）をsymbolsで9月窓と2026〜2027年窓に指定しても**全件0件**でした。期間の狭さでは説明できず原因未確定で、0件を無配当と解釈しません。marketをlimit5へ増やすと5行になりましたがtotalCount/cursorがなく、日本株配当の全件網羅は未確認です。`dividend_amount`はupcoming額（なければrecent額）と一致する例があり、**正式な優先規則は未確認**。またmarketの`dividends_yield`とrawの`dividends_yield_current`には大きな値差の例があり、同一指標と決めつけません。`*_recent`と`*_upcoming`の日付・金額は同じsuffix同士で扱い、recent権利落ち日にgeneric金額を自動紐付けしません。

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

対応する単一条件は[標準JSON](SCREENING_MANUAL.md)が第一候補です。条件名・取得列・Presetの違いは[条件カタログ](SCREENER_CONDITIONS.md)を使い、公式MCPの直接取得→既存Readの組合せ→必要時の公式OHLCVからの計算を調べます。元の母集団・条件が成立しなければ、未確認と非対応を区別して制約を報告します。外部データは自動フォールバックせず、明示的な依頼・承諾後だけ別拡張として利用します。判断規則の正本は[AIガイド](AI_JSON_GUIDE.md)です。

既存指標はget_symbol_data/batchやget_technicals_ratingで調べ、期間・足が合えば再計算を避けます。SMA25等が直接取れなければget_ohlcvによるローカルPython計算も選択肢です。NaN/欠損・25確定日足・時系列・重複・日時・価格調整を検証し、部分結果を全件成功としません。

財務履歴、経済時系列、ニュース、文書、各カレンダーは用途の異なるReadです。取得可能な過去/将来期間、通貨・単位、公開/更新時点、利用権限を確認し、任意応答を標準Screening履歴対応と説明しません。

### 既存ラッパーを呼ぶRead例

これは既存認証を利用して1銘柄の日足を日付範囲・columns形式で読む例です。ファイルの作成/実行が依頼された時だけ、実際の保存先・環境・起動コマンド・結果保存先を提示して実行します。以下の関数定義だけではデータ取得や結果保存は行いません。

```python
from tradingview_screening.integrations.tradingview.client import TradingViewClient
from tradingview_screening.integrations.tradingview.schemas import GetOhlcvRequest

async def read_window():
    async with TradingViewClient() as client:
        response = await client.get_ohlcv(GetOhlcvRequest(
            symbol="TSE:7203", interval="1D", count=3, summary=False,
            date_from="2026-10-05", date_to="2026-10-09", format="columns",
        ))
        data = response.model_dump(mode="json")["structured_content"]
        if not isinstance(data, dict) or data.get("success") is not True:
            raise RuntimeError("OHLCV取得失敗または応答構造の不一致")
        return data  # bars/has_more/next_date_toを確認し、全件か部分取得かを判断する
```

Windowsのコマンドプロンプトではリポジトリルートで`call scripts\setenv.bat`後の`"%PYTHON_EXECUTABLE%"`を使います。通常Screeningは`app.bat screen <name>`で実行します。独自Pythonをscreen/Jobへ渡さず、[AIガイドの起動・実行契約](AI_JSON_GUIDE.md#作成して実行の完了契約)に従います。

### 第3ラウンド公式MCP直接観測：株式以外の識別子と時系列

以下は**公式MCPへの直接接続**で得た数値Readと各3本のOHLCV成功例です。ラッパー側の新規成功ではなく、未実行の時間足へ一般化しません。

| 対象 | Quote/OHLCVに成功したシンボル | OHLCV時間足 | データ解釈上の注意 |
| --- | --- | --- | --- |
| 日経225ミニ連続先物 | `OSE:NK225M1!` | 1D | 現物日経・通常先物と別契約。`update_mode:delayed_streaming_900` |
| NASDAQ 100連続先物 | `CME_MINI:NQ1!` | 4h | 限月付き`NQZ2026`とはEMA50が異なる |
| 金連続先物 | `COMEX:GC1!` | 1h | 現物XAUUSDではない。`GCZ2026`とEMA50に差 |
| WTI原油連続先物 | `NYMEX:CL1!` | 1D | Micro WTIの`MCL`とは別、`CLZ2026`とEMA50/SMA25に差 |
| USDJPY | `FX:USDJPY` | 4h | volumeは数値だが単位未確認 |
| 米10年国債利回り | `TVC:US10Y` | 1D | volume・標準RSI/SMA25/EMA50はnull。`change`は利回り水準の増減幅ではなく相対変化率の実例 |
| ドル指数 | `TVC:DXY` | 1h | `type:index/subtype:cfd`。volumeはnull、ICEUS版との同一性未確認 |

調査では`run_screener`の`market:futures/forex/cfd/bonds`がそれぞれ応答しましたが、市場名を純粋な商品種別と扱えません。実際`market:cfd`でCRYPTOCAPの暗号資産時価総額指数が返りました。`type/subtype/typespecs/exchange`を照合してください。連続・限月先物は同じcloseでも指標履歴が異なり、ロール/接続・調整方式は未確認です。債券利回りの`change`を利回りのパーセントポイント変化と読み替えず、null出来高をゼロに補完しません。遅延表記の数値単位、取引時間、足確定の厳密条件は未検証です。

### 第4ラウンド公式MCP直接観測：OHLCV形式差と指標の再現性

2026-10-27 21:25〜21:29 JSTに公式MCP直接Readを3種類・27回（全件Provider `success:true`、Writeなし）実施し、Toyota（`TSE:7203`）/Apple（`NASDAQ:AAPL`）の1D・1h・4hの600本OHLCVと直接指標を照合しました。**本ラッパーの追加実行結果ではありません。** 結果の一致許容誤差は絶対`1e-8`です。

- **日足：** 両銘柄のRSI7、既定RSI（14期間Wilder候補）、SMA13、EMA13/25、MACD本線/シグナルがすべて一致。これは試験した銘柄・時点・計算定義での結果です。
- **Toyota 1h・4h：** 1hの2026-10-23 15:00 JSTバーは`rows`のclose=3105/volume=8,365,100に対し`columns`のclose=3096/volume=1,393,000。4hの2026-10-02 13:00 JSTバーは`rows`のclose=2856.5/volume=14,758,300、`columns`のclose=2867/volume=6,343,600。各volume差は同日15:30の30mバーに一致。`columns`600本の該当close各1か所を**実取得したrowsの値にローカル診断用として置換**すると、各時間足の7指標すべてが直接値と一致しました（Providerには書き戻していない）。引けオークションやキャッシュ等、Provider内部原因は未確定です。Toyota全600本のrowsを通算検査したわけではありません。
- **Apple 1h・4h：** 各600本の`rows`と`columns`は全OHLCVが一致しましたが、RSI/SMA/EMA/MACDの各7項目は直接指標と不一致のままです。`close|60`/`close|240`は343.98、OHLCV最終closeは343.99であり、米国株の価格系列/配信元等の原因は未確定。日足と日中足の終値・volumeも同一視できません。**rowsを全銘柄の真値・自動修復先として固定しません。**
- **Tech Rating：** 1h/4hを指定した`get_technicals_rating`のRSI・MACD本線/シグナルは同時間足のbatch値と一致しましたが、同Toolのprice/volumeは日足相当でした。レスポンス内フィールドの時間足粒度を混同しません。
- **時刻・確定足：** `t`はバー開始時刻に対応する観測。Toyotaには昼休みと15:30の30mバー、AppleにはDSTに伴うUTC時刻の切替と4h最終区間の端数があります。`is_closed`/`barstate.isconfirmed`/調整係数の候補列は試験ではnull。Provider `update_time`は時間足ごとのバー終了や確定時刻を保証しません。
- **カーソル：** `next_date_to`をそのまま次回`date_to`に渡し、Toyota 1hの600本＋遡り5本で重複0・継続を確認。ただし履歴の全期間・全銘柄の保証ではありません。生データ実取得の最大は600本で、公開Tool説明のrows5000/columns8000の上限到達は未試験です。
- **長期RSI：** ローカルWilder RSI48/96/192は取得600本でもseed・履歴長の感度が残りました。例えばApple 1h RSI96の600本でseed差約0.244、RSI192では約5.165。これは**ローカル計算値のみ**であり、公式Provider RSI48/96/192の直接列に成功した証拠ではありません。必要な履歴を追加し、結果の収束を計測します。固定本数で精度を保証しません。

重要な判定は**成功応答とデータ整合性は別**という点です。OHLCVのformat、取得した期間、UTC時点、セッション、バー確定状態、基礎系列と再計算指標を記録し、不一致のまま自動で直接指標と同一視しないでください。実行根拠は会話添付`tradingview_mcp_capability_matrix_round4.md`／`tradingview_mcp_probe_evidence_round4.json`（調査用データはGitHubに転載しない）です。

### 第5ラウンド公式MCP直接観測：日本株の予想・財務・イベント品質

2026-10-27 21:36〜21:37 JSTに公式MCP直接Read **9種類・20回**を実施。Provider `success:true`16件、`success:false`1件（列Discoveryで`currency`検索が該当なし）、`success`キーなし3件（文書系）。**MCP `isError:false` は20件すべて**。Write・ラッパー経由の新規テスト・製品コード変更はありません。

- **予想値：** 日本株4銘柄の共通倍率は次FQ/EPS・売上`157.4059499449`倍、次FY/EPS・売上`158.7805652588`倍、EPS TTM`162.6280696048`倍（raw値 ÷ `get_forecasts`値）。倍率の原因は不明であり、**FX換算の証明・自動補正係数ではありません**。円表示だけで単位や期間を確定しない。TSM ADRは値があるFQ/FY予想のraw/forecast一致、基本EPS TTMは双方nullで「一致した値」に数えない。
- **財務期間・EPS：** `period:ttm`でも裸`net_income`はFYと一致しTTMとは異なる（トヨタ/Apple）。`period`切替時はraw名のmetricを渡しても返却suffixが切り替わり得ます。Apple FY履歴EPS=7.465は希薄化後EPSと一致、`eps` aliasで返る基本EPS=7.4931とは異なります。全体の統一ルールとは断定せず、suffix・会計期末・基本/希薄化後を毎回保存します。
- **年度ラベルと文書：** Toyotaの財務履歴FYラベル`2025`は末尾raw実績FY期末2026-03-31、文書FY2026 Q4と対応し、ラベルをそのまま企業FY名へ置き換えるとずれます。Toy​​ota文書要約の「売上・純利益とも前年比増加」は同年度の純利益実績の前年比**19.2439%減**と矛盾しました。原本PDFは未照合のため、要約もraw履歴も正本扱いしないでください。
- **決算予定：** 同じ10〜12月窓内にraw次回日があるトヨタ（11/5）・ソニー（11/10）が`get_earnings_calendar`で欠落、Apple（11/2）は返却。イベントの0件を「予定なし」へ変換しない。
- **配当予定：** 日本株のmarket指定では9月窓で3銘柄（追加検証では5行）が取得できた一方、そのうち3銘柄はsymbols指定の同じ窓・広い窓で0件。recent/upcomingのex-date・payment-date・amountは対応suffix同士を比較した3銘柄でraw値と一致（null同士の一致は取得成功とは数えない）。同日の支払日表示の確定性、generic額/yieldの定義、market全件性は未確認。
- **Discovery不一致：** `get_screener_columns(search=currency,market=stock)`は該当なしでも`get_symbol_data_batch`で`currency`と`fundamental_currency_code`が9銘柄とも非null。カタログ検索の空をフィールド取得非対応とは扱いません。

AI企業分析では、確認できた**実績の明示suffix値**を、通貨・期末・EPS定義を保持して条件付き採用します。raw予想・生の目標株価・カレンダー・配当は検証待ちとし、日本株`get_forecasts`の未検証単位による自動評価、品質ガード迂回、カレンダー0件による通知抑止、要約の増減方向の無検証採用を避けます。調査証跡は会話添付`tradingview_mcp_capability_matrix_round5.md`と`tradingview_mcp_probe_evidence_round5.json`（GitHubに生応答全文を転載しない）です。

### JPYUSD終値と日本株forecastの20件一致（公式MCP追加観測）

10/27 22:16〜22:18 JSTの公式MCP直接Readは**3種類・15回、全件Provider success:true、Write/設定変更0**でした。前回の日本株forecastとraw数値は再取得せず、第5ラウンドの証跡を再利用しています。為替の数値は公式MCPの`get_ohlcv`で`FX_IDC:JPYUSD`の該当期間を取得し、同じraw/forecast比較で確認しました。

| 比較した項目 | 期末候補日（バー開始日はUTC前日22:00） | `FX_IDC:JPYUSD`の終値 | raw / forecast |
| --- | --- | ---: | ---: |
| 次FQ予想EPS・売上 | 2026-09-30 | `0.006353` | `157.40594994490792` |
| 次FY予想EPS・売上 | 2026-03-31 | `0.006298` | `158.78056525881232` |
| 実績EPS TTM | 2026-06-30 | `0.006149` | `162.6280696048138` |

トヨタ・ソニー・三菱UFJ・日立の各5項目（EPS次FQ/FY/TTM、売上次FQ/FY）すべてで`raw × 上記の日足終値 = get_forecasts`がPython floatで完全一致し、20/20・誤差0でした。例：日立EPS TTM `176.9908 × 0.006149 = 1.0883164292`。Decimalの文字列表現まで厳密一致するとは主張しません。`FX:USDJPY`と`FX_IDC:USDJPY`の日足・比較した1h OHLCには逆数の厳密一致がなく、バー時刻と価格提供元も異なります。Pineの[通貨変換説明](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/#currency)は本MCPの内部計算契約を証明するものではありません。

数値モデルを再現できたことと**MCPが内部でこの系列を使っていることの因果的証明**を区別します。`JPY`通貨ラベル、次FY予想への直近FY末レート適用、原データ/変換後データの由来、`target_mismatch`の内部条件は未解明。`get_forecasts`のJPYラベル値をそのまま円建て予想PER・EPSへ利用せず、固定レート補正も実装しません。

別の重要なOHLCV上の注意として、1hのRFC3339 `date_to`を指定した3回はいずれも、要求した時刻の**後**に開始する23本を含む32本を返しました（`has_more:true`、指定窓内52本のうち一部）。Provider `success:true`だけで「指定時刻までに制限された」と判断せず、返却`t`と要求範囲を自前で検査してください。実測根拠は会話添付`tradingview_mcp_fx_conversion_validation.md`／`tradingview_mcp_fx_conversion_evidence.json`。提供元の生応答全文は本リポジトリに転載しません。

## Provider制限・プラン・安全性

全Toolにインターネット・公式MCP対象プラン・保存済み認証・Tool権限が必要です。公開資料ではEssential以上/試用プラン除外と案内されていますが、契約条件は公式ページで再確認してください。これはAIへの別途サーバー登録を求める意味ではありません。

Providerの目安は約100要求/分、アプリ既定Governorは30要求/分・同時1・試行Timeout30秒・最大3試行です。接続/OAuth段階の待ち時間は別で、実行全体が30秒以内とは限りません。Writeは自動Retry/cache対象外。Readも既存Governorを経由し、検証のために無制限の並列/全銘柄取得をしません。

無条件全米株Screenerの拒否と最大1000行は[現行の制約](SCREENING_MANUAL.md#公式mcp-beta版のスクリーニング制限2026-10-18実機確認)。他のラッパーで同じ母集団を確定できるかは別調査で、S&P 500へ勝手に縮小しません。Watchlist/Alertの個人情報や生応答・tokenをチャット/commitへ載せません。

## 公式資料・実装・Discoveryの差分

| 項目 | 照合結果と扱い |
| --- | --- |
| Tool集合 | 公開資料・ローカル・2026-10-27 Discoveryの35名が一致。不足/追加は0。live109引数に対しローカル110引数で、差は保持したWatchlistのdescription。全Toolの実行成功を示すものではない |
| get_ohlcvの追加引数 | 2026-10-27再閲覧の公開ページはcount上限5000・symbol/interval/count/summaryを記載。date_from/date_to/formatは公開ページに未掲載だが、Discoveryと少量Readを根拠に既存Requestで対応済み。countもrows5000/columns8000へ対応。8000本の実取得成功を主張しない |
| update_watchlist.description | 公開ページと現行Requestにはあるが、当日Discoveryにはない。Writeを実行しての可否検証はしていない |
| Alert追加キー | ローカルCreateはwebhook/monitor、Updateはwebhookを受理し得るが、公開ページはwebhook等を制限。Schema適合を実行成功としない |
| NULL・型・上限 | ローカルには必須nullableや公開資料で未指定の上限がある。表はローカル契約、意味的な成功はProvider側で別途確認 |
| 応答 | Read包絡の型検証はあるが、全35 Toolの完全な出力Schema/全キーは固定していない。公開説明と実応答を混同しない |
| ScreenerのSMA25と市場区分 | 公式公開ページは`SMA25`の直接取得、`price_vs_sma25_pct`や`market_segment`のfilter可否を個別に明記していない。10/27の別環境の公式MCP直接ReadではSMA25値をScreener/単体/一括取得でき、上記2filterはignored_filtersで無視された。詳細は[条件カタログ](SCREENER_CONDITIONS.md) |

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

2026-10-27 08:43〜08:44 JSTには、既存ClientからOHLCV10回と、batch/財務/news/経済symbol/経済calendar各1回、計6 Tool・15回の少量Readを追加しました。success=true 13回、未知OHLCV銘柄のsuccess=false 1回、経済calendarのstatus=ok 1回です。batchは取得1・missing 1を保持しました。上表は10/26時点の記録であり、今回も全35 Tool・全市場・全件の成功を検証したものではありません。機能を変更しない今回の文書統合では、この既存結果を再利用しています。

2026-10-27の**別環境での公式MCP直接利用**の実行記録では、35 ToolのうちRead 6種類・計40回を呼び出し、`SMA25`の値取得、東証株を価格帯に分割した3,761件の取得と3,748件の乖離率計算を行いました。プライム所属は確認できず、34件の+20%以上候補をプライム該当と断定していません。これは**本リポジトリのClientを用いた追加実機検証ではない**ため、上表の10/26既存ラッパーの検証件数には合算しません。実機データの大規模転載は行わず、利用可能性と制約だけを[条件カタログ](SCREENER_CONDITIONS.md)に反映します。

Beta更新時は公式ページのTool集合と既存TOOL_NAME_MAP/REQUEST_MODELSを比較し、既存Client.list_tools()の名前・inputSchema・不足/追加を照合します。列探索は概要→必要なgroup/search、filterは少数取得でignored_filters・実値・単位・件数を検証します。差分を記録し、型やCLIの拡張が必要なら別のdevelop向け実装として扱います。公式説明や生schemaの長文保存物をそのまま配布しません。

技術契約は[既存Client](../../src/tradingview_screening/integrations/tradingview/client.py)・[Request/Response](../../src/tradingview_screening/integrations/tradingview/schemas.py)・[Governor](../../src/tradingview_screening/common/request_governor.py)、開発向け解説は[developのAPI資料](https://github.com/TakamKaji/tradingview_mcp_support/blob/develop/docs/development/API.md)を参照します。

[条件カタログ](SCREENER_CONDITIONS.md) / [利用者マニュアル](README.md)
