# 共通機能・同梱サンプル・公式Toolの対応範囲

本ツールの共通機能、設定の使用例、Python APIだけにある操作を分けて説明します。公式MCPにToolがあることと、本ツールのCLIや定期Jobからそのまま使えることは別です。

Windowsネイティブは[setup.batから導入](WINDOWS_SETUP.md)、Dockerコンテナは[Docker導入手順](DOCKER.md)から実行します。コンテナ内では共通CLIの認証・Screening・保存結果・手動Jobを使えますが、Windows Task Schedulerによる定期登録は使いません。

## A. 本体の共通機能

| 機能 | 利用する入口 | 利用者が決めること・副作用 |
| --- | --- | --- |
| 公式MCP認証・接続確認 | setup.bat、mcp auth/status/tools | authはブラウザ認可。status/toolsは接続・一覧確認 |
| 名前付きScreening | screen | market・条件・並び順・件数・列をJSONに定義。Read＋結果保存 |
| 保存結果の参照 | results latest/history/compare | Screening名を指定。ローカルReadのみ |
| 管理Watchlist差分同期 | 同期を有効にしたScreening Job | 管理対象の銘柄を追加・削除するWrite |
| Job Runner | run、jobs list | 対象Screening、保存・同期をJob JSONで設定 |
| Windows定期登録 | schedule apply/list/remove | 日次・Asia/Tokyo・ログオン中。apply/removeはTaskの作成/更新・削除 |

条件定義とJobの時刻は利用者が設定します。履歴比較は同じ条件の直近2成功結果を対象にし、条件が異なる・旧形式で確認できない場合は比較不能を返します。不完全取得の差分は観測した集合の差で、条件への不適合を断定しません。

## B. 同梱サンプル

`screenings/`の日本株割安・S&P 500・公式preset等は条件の使用例、`jobs/`の日次設定はJobの使用例です。特定条件・実行時刻を固定した監視サービスではありません。コピーして別名・別条件・別時刻で使えます。

[Screeningの全文例](SCREENING_MANUAL.md#自分の条件を追加する)と[Jobの全文例](SCHEDULE_MANUAL.md#自分のjobを作る)から、自分の定義を作成してください。同梱の`sample_screen_daily`は初期設定で定期登録対象かつWatchlist Writeありなので、登録前に全Jobを確認します。`us_sector_morning`はProvider制約で無効であり、全米株集計を利用できるサンプルとして扱いません。

## C. 公式Toolと本ツールの接続範囲

[公式MCP資料](https://www.tradingview.com/mcp/docs)に対応する、下記35 Toolの型付きRequest・Pythonラッパーを実装しています。CLIは`mcp auth/status/tools`、`screen`、`results`、`run`、`jobs list`、`schedule`に限られ、任意Tool名を直接実行するコマンドではありません。`mcp tools`はTool一覧を表示し、一覧内のToolを実行する操作ではありません。

| 公式Tool（すべてPythonラッパーあり） | 現行CLIからの利用 | Job / Schedulerとの接続 |
| --- | --- | --- |
| Screener：`run_screener` | screen、Screening Jobのrunで内部利用 | Screening Jobに接続済み |
| 銘柄・列・評価：`get_symbol_data`、`get_symbol_data_batch`、`get_screener_columns`、`get_technicals_rating` | 個別実行CLIなし | 任意取得Jobなし。get_screener_columnsだけは全米株builtin内部の列確認に利用（本番取得はProvider制約で未対応） |
| ローソク足・経済：`get_ohlcv`、`get_economic_data`、`get_economic_symbols` | 個別実行CLIなし | 定期取得Job・同梱サンプルなし |
| 銘柄検索：`search_symbols` | 個別実行CLIなし | 定期取得Jobなし |
| Watchlist：`list_watchlists`、`get_watchlist`、`get_active_watchlist`、`create_watchlist`、`delete_watchlist`、`add_to_watchlist`、`remove_from_watchlist`、`update_watchlist` | 任意操作CLIなし。同期は設定したScreening Jobから実行 | 同期処理のcreate/get/add/removeのみ接続。削除・名前変更・active変更は通常同期に含まない |
| ニュース：`get_news`、`get_news_story` | 個別実行CLIなし | 定期取得Job・同梱サンプルなし |
| 予想・財務：`get_forecasts`、`get_financials`、`get_financial_history` | 個別実行CLIなし | 定期取得Job・同梱サンプルなし |
| 文書：`get_documents`、`get_document_view` | 個別実行CLIなし | 定期取得Jobなし |
| カレンダー：`get_earnings_calendar`、`get_economic_calendar`、`get_dividends_calendar` | 個別実行CLIなし | 定期取得Jobなし |
| Alert：`create_alert`、`update_alert`、`delete_alert`、`stop_alerts`、`restart_alerts`、`list_alerts`、`get_alerts`、`get_alerts_log` | 個別実行CLIなし | Alert操作Jobなし |

Pythonラッパーはアプリへ組み込むためのAPIです。既存の認証と通信制御を通して呼び出します。APIが実装されていても、Providerの利用権限・Tool公開状況・引数による成功可否は別です。取得した任意Toolの結果を、Screening用の保存・履歴比較へ自動で流す機能もありません。

### ローソク足取得の範囲

公式`get_ohlcv`は指定銘柄・時間足の始値、高値、安値、終値、出来高を取得するRead Toolです。本ツールには`TradingViewClient.get_ohlcv`と`GetOhlcvRequest`があります。従来の`symbol`、`interval`、`count`、`summary`に加え、`date_from`・`date_to`で両端を含む日付範囲、`format`で`rows`（足ごとの配列）/`columns`（各項目の配列）を指定できます。日付は有効な`YYYY-MM-DD`または時差付きRFC3339です。count上限は形式省略/rowsで5000、columnsで8000です。新引数を省略すれば従来どおりProviderの既定値を使います。

2026-10-27の既存Clientによる少量Readで、日付指定・両形式の値の一致・columnsのcount=8000指定（実取得5本）を確認しました。8000本全件の取得保証ではありません。応答の`has_more`・`next_date_to`を確認し、遡る場合も日時・重複・欠損・完全性を検証してください。Providerの新しい引数がすべてラッパーに追加されているとは限りません。

**本ツールのCLIにはローソク足取得コマンドがなく、Jobのtask.definitionにget_ohlcvを指定して動かすこともできません。** 定期取得、ローソク足の自動ファイル保存・履歴管理を行うJobは未実装です。ニュース・財務・評価指標も、Python APIの存在だけで定期Job対応とは扱いません。

Python APIの実装は[client.py](../../src/tradingview_screening/integrations/tradingview/client.py)と[schemas.py](../../src/tradingview_screening/integrations/tradingview/schemas.py)、詳しい組み込み方法は[developのAPI資料](https://github.com/TakamKaji/tradingview_mcp_support/blob/develop/docs/development/API.md)を参照してください。Write APIの利用には対象と副作用の確認が必要です。`get_active_watchlist`もProvider説明上activate/createを伴う場合があるため、安全なRead-only例として使いません。

[利用者マニュアル一覧](README.md)
