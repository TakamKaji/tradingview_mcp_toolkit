# 保存結果・Phase 9の実測記録

> 各日付時点の記録です。PR #19は後日mainへ統合済みです。前半の未実施・Draft記述は追加試験前の状態を保持しており、最後の追加実機確認と区別してください。現在も全米株本番は未対応です。[記録索引](README.md)へ戻る。

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

### 2026-10-18 23:02〜23:03 JST 追加実機確認

- 本番の `app.bat run us_sector_morning`：現行公式MCPは条件なしの `america/stock` 取得を拒否し、`PROVIDER_ERROR` / exit 1、JSON保存なし。実行と通信は正常に到達。
- 検証専用S&P 500：`filters.index="S&P 500"`、`totalCount=returnedCount=uniqueSymbolCount=503`、無視されたfilterなし。TradingView sector分類20件、有効503件・除外0件。各平均・件数・rankを独立照合し、JSON保存と読み戻し成功。
- これは **S&P 500限定での成功** であり、全米株本番summaryの成功ではない。Beta公開サンプルは `enabled=false` とし、Provider更新により全Universeの取得方法が確立するまで定期登録しない。
- [Issue #18の検証根拠](https://github.com/TakamKaji/tradingview_mcp_support/issues/18#issuecomment-6250858944) を参照。
