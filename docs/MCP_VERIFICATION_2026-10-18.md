# TradingView公式MCP再検証（2026-10-18）

## 方法

Windows Embedded Python 3.12.8、既存TradingViewClientと共通RequestGovernor、通常ユーザーの保存済みcredentialで少量Readを実施しました。直接のAI用MCP connectorは使用していません。Watchlist/Alert Write、Scheduler登録・削除も行っていません。市場データ本文、credential、個人IDはコミットしていません。

## Discoveryとschema

- OAuth認証成功、protocolVersion=2025-11-25、serverVersion=1.30.0。
- 35 Tool、expectedMissing / unexpectedAvailableは空。
- run_screener / get_screener_columnsのinputSchemaは2026-09-25 snapshotと同一。
- Screenerはfilters / filter_preset / symbolsetを持ち、limit上限1000。pagination / offset / cursorはありません。
- 5 Tool（dividends/earnings/economic calendar、economic data、financial history）は日付の説明だけが変更。
- get_ohlcvには任意date_from/date_to/formatが追加され、countの説明も変更。既存wrapper呼出は互換ですが、このScreening拡張では新OHLCVオプションを実装していません。
- 実測inputSchemaはtests/fixturesの2026-10-18 snapshotに保存。固定35 Tool契約と新旧schemaの差分をテストします。

公式公開リファレンス: [TradingView MCP docs](https://www.tradingview.com/mcp/docs)。動作判定は取得済みschemaと実Python clientの応答を根拠にします。

## カラム

stock指定は17グループ/163カラム、market省略のallは17グループ/292カラムでした。これらは観測値であり、将来も固定件数を要求しません。

| 用途 | name | カタログの対応market |
| --- | --- | --- |
| セクター | sector | stock, bond |
| 騰落率 | change | stock, etf, coin, crypto-cex, crypto-dex |
| PER | price_earnings_ttm | stock |
| 予想配当利回り | dividends_yield | stock, etf |
| TTM配当利回り | dividends_yield_ttm | stock |
| RSI | RSI | stock, etf, coin, crypto-cex, crypto-dex |
| 出来高 | volume | stock, etf, bond |

EMA検索は部分文字列一致のpremarket列を返し、EMA50/EMA200をカタログから発見できませんでした。一方、oversold_healthyの既定実応答にはEMA50、EMA200、price_vs_ema50_pct、price_vs_ema200_pctがあり、公開preset例はこの実測名を使います。アプリ側では再計算しません。

## 少量要求の実測

| テスト | Provider success | totalCount | returnedCount | 判定 |
| --- | --- | --- | --- | --- |
| japan、pe=[0,15] / div_yield=[3,null] | true | 1037 | 5 | 全5件がPER/予想配当条件に適合、出来高降順 |
| america、index=S&P 500 | true | 503 | 5 | rowsはobject配列、symbolはEXCHANGE:TICKER、sectorは文字列 |
| america、oversold_healthy | true | 115 | 5 | preset認識、RSI/EMA/EMA乖離率キーあり |
| america、symbolset=[SYML:SP;SPX] | true | 503 | 5 | 明示Universe指定に成功 |
| america/stock、条件全省略 | false | — | — | Provider業務拒否。transport/OAuth成功とは区別 |
| japan、dividends_yield_ttmをfilter指定 | true | 1855 | 5 | ignored_filtersが非空、要求条件未成立のためアプリでは失敗扱い |

各成功要求のlimitは5です。totalCountは要求条件に対するProvider申告値であり、5件の取得から全件取得を推定していません。構造はstructured_content.success、data.rows、data.totalCount、追加fieldはignored_filters等です。

拡張後は公開Job4件を `app.bat run` 経由でも再実行し、すべてsuccess / exit 0 / saved=true / Watchlist同期なしを確認しました。requestedLimit=5、returnedCount=5、limitReached=true、completeCoverage=falseで保存され、上表のtotalCountと一致しました。日本株の条件適合、presetの明示要求RSI/EMA/乖離率列も確認済みです。

## Phase 9の判断

sector/change列とS&P 500に限定した少量データは取得できました。しかし条件なしのamerica/stockは拒否され、1000件を超える全米株Universeを完全取得する公式手段は確認できません。S&P 500、先頭1000件、未検証のfilter分割を代替Universeにしません。

Issue #18 / PR #19は引き続きblocking limitationを保持しDraftのままとします。全米株集計のlive保存は未実施です。一般Screeningの成功とPhase 9の全Universe保証は別々に判定します。
