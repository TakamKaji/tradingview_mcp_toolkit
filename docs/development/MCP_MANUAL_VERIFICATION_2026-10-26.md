# 公式MCPマニュアル・条件カタログの検証（2026-10-26）

対象：[公式MCP機能マニュアル](../user/OFFICIAL_MCP_MANUAL.md)・[条件カタログ](../user/SCREENER_CONDITIONS.md)・[AIガイド](../user/AI_JSON_GUIDE.md)。利用者向け説明の正本はこれらの文書です。この記録はdevelop専用で、mainへの配布対象には含めません。

## 基点・環境・安全境界

- PR #62はdevelopへsquash merge済み。基点は`0a8cf09a072fe1e1be2264ab02b8c8505db03f71`。そこから`codex/official-mcp-manual-catalog`を作成。
- 調査時のorigin/mainは`b7ecd7ecabb79b12634739adb353a144b7027295`。mainへの取り込み・merge・tag・Release・公開操作は行わない。
- Windows、既存Embedded Python 3.12.8、既存の保存済み認証、`TradingViewClient`、型付きRequest、既定RequestGovernorを使用。システムPythonや追加依存を使わない。
- 初回sandbox内の`app.bat mcp status`は接続待ちとなり、約426秒で中断。ネットワークを利用可能な環境で既存Clientのstatusを90秒の上限付きで再実行し、exit 0・authenticated=true・toolDiscoveryAvailable=trueを確認。認証の再設定・資格情報の削除や手動変更はしていない。
- 個別実行はReadのみ。Watchlist/AlertのWrite 10 Tool、active Watchlistのactivate/create、Scheduler登録/削除は実行しない。大規模母集団取得・JPX取得もしていない。
- 生のProvider応答・公式説明全文・認証情報はcommitしない。以下にはRequestと集計・構造だけを記録する。

## 根拠と全35 Toolの照合

[公式ページ](https://www.tradingview.com/mcp/docs)を2026-10-26 JSTに確認。既存[Client](../../src/tradingview_screening/integrations/tradingview/client.py)、[Request/Response](../../src/tradingview_screening/integrations/tradingview/schemas.py)、[Tool名写像](../../src/tradingview_screening/integrations/tradingview/tool_catalog.py)、FEATURES、SCREENING_MANUAL、AI_JSON_GUIDE、開発API資料を照合した。

2026-10-26T14:12:33.642729+00:00のDiscoveryは35 Tool、不足0・追加0。公開論理名35・ローカルラッパー35・型付きRequest35が対応。新マニュアルは35個のTool節・107個の引数行を持ち、現行Requestの必須性・nullable・enum・上限と照合した。正式名は公開論理名、wire名は既存写像に従う。

| 差分 | 今回の証拠と扱い |
| --- | --- |
| OHLCV追加引数 | live inputSchemaにはdate_from/date_to/formatがあり、公開ページと現行Requestにはない。既存Requestからの利用は未対応。追加キーは送信しなかった |
| Watchlist説明更新 | 公開ページとUpdateWatchlistRequestにdescriptionがあるが、live inputSchemaにはない。実行による判定は未実施 |
| 制約の省略 | live inputSchemaではenum/上限/既定値が省略される箇所がある。現行ローカル検証契約を解除する根拠とはしない |
| Alertの追加キー | ローカルの特定pattern extraと公開ページの制限を区別。Schema適合をProviderでの成功と扱わない。Write未実施 |

全35 Toolの実行検証を意味しない。列/指標以外のニュース、財務、文書、カレンダー、経済データ等は、公開資料・ローカル契約・Discoveryの確認のみ。

## 少量Readの再現条件・結果

実行時間帯は23:12〜23:16 JST（UTC 14:12〜14:16）。接続/Discoveryを除く個別Tool呼出しは**16回・6 Tool**。success=trueは14回、「一致列なし」のProvider失敗は2回。successのうち無視されたfilter指定2回を条件成功から除外する。

### 列探索：6回

すべて`GetScreenerColumnsRequest(market="stock", ...)`。

| 追加引数 | 結果 |
| --- | --- |
| なし | success、17分類・163列 |
| group="valuation" | success、20列、markets/variants/説明等を確認 |
| group="technicals" | success、26列、時間足派生の説明等を確認 |
| search="SMA" | success=false、一致列なし。SMA全般の非対応とはしない |
| search="EMA" | success、premarketの部分一致5列のみ。EMA不存在の証拠にはしない |
| search="prime" | success=false、一致列なし。プライム指定全般の非対応とはしない |

17分類の全件数と主条件32項目はカタログに収録。stock指定でもbonds/ETF等の分類が含まれるため、分類名だけで市場別対応を保証しない。

### Screener：6回

最初の5回の共通Requestは`RunScreenerRequest(market="japan", symbol_types=["stock"], sort_by="volume", sort_order="desc", limit=3, filters=下表, columns=[対応列,"volume"])`。

| filters | 対応列 | 取得行 / totalCount | 意味的検証 |
| --- | --- | --- | --- |
| {"pe":[0,15]} | price_earnings_ttm | 3 / 1904 | 全3値が有限・0〜15、出来高降順 |
| {"div_yield":[3,null]} | dividends_yield | 3 / 1554 | 全3値が有限・3%以上、出来高降順 |
| {"rsi":[null,40]} | RSI | 3 / 1304 | 全3値が有限・40以下、出来高降順。期間14との同一性は未検証 |
| {"price_book_fq":[0,1]} | price_book_fq | 3 / 3896 | ignored_filtersに当該キー、全3値が1超。不合格 |
| {"dividends_yield_ttm":[3,null]} | dividends_yield_ttm | 3 / 3896 | ignored_filtersに当該キー、全3値null。不合格 |

上3回はignored_filtersの申告なし。申告の有無だけでなく実値を照合した。下2回はそのキーの無視を確認したのであり、別aliasや値取得後のPython判定まで不可能とはしない。既存Engineの正規化は非空ignored_filtersをMCP_SCHEMA_MISMATCHとして拒否する。

6回目は`RunScreenerRequest(market="america", filter_preset="oversold_healthy", limit=3, columns=["close","RSI","EMA50","EMA200","price_vs_ema50_pct","price_vs_ema200_pct"])`。success、3 / totalCount 181、指定presetの認識とEMA/乖離率の値を確認。全内部条件・残る5presetの実行は未検証。要求していないEMA等の追加項目も返るため、追加応答項目と正式指定列/filter対応を同一視しない。

### 単体・一括・テクニカル・日足：各1回

| 型付きRequest | 結果・範囲 |
| --- | --- |
| GetSymbolDataRequest(symbol="TSE:7203", columns=["close","RSI","RSIの1h派生列","MACD.macd","Volatility.D"]) | 全5値が数値。1h列の正確な表記は下記。filter対応・RSI14との同一性は別 |
| GetSymbolDataBatchRequest(symbols=["TSE:7203","TSE:6758"], columns=["close","RSI","price_book_fq"]) | count=2、missing_count=0、missing=[]。部分失敗/未知銘柄の回復試験なし |
| GetTechnicalsRatingRequest(symbol="TSE:7203", interval="1D") | moving_averagesにSMA20/50等、oscillatorsにRSI/MACD等の項目を確認。当該応答にSMA25なし |
| GetOhlcvRequest(symbol="TSE:7203", interval="1D", count=30, summary=False) | count=30、structured_content直下にbars、各足t/o/h/l/c/v。tは整数UTC Unix秒。30本のOHLCVは有限、日時重複なし・昇順。2026-09-09〜2026-10-26 UTCの日時範囲。確定足・価格調整・取引日網羅は未検証 |

1h列の完全な文字列（縦棒はU+007C）：

```text
RSI|60
```

同じ調査を行う場合は、リポジトリルートのコマンドプロンプトで以下を実行する。上記表のnullはPythonではNoneにする。Readスクリプトの保存先は実際に作成したパスに置換する。以下の例は1回のPER試験だけで、生応答を表示しない。

```bat
app.bat mcp status
call scripts\setenv.bat
"%PYTHON_EXECUTABLE%" .local\probe_per.py
```

`.local/probe_per.py`として保存する例：

```python
import asyncio
import math
from tradingview_screening.integrations.tradingview.client import TradingViewClient
from tradingview_screening.integrations.tradingview.schemas import RunScreenerRequest

async def main():
    async with TradingViewClient() as client:
        response = await client.run_screener(RunScreenerRequest(
            market="japan", symbol_types=["stock"], filters={"pe": [0, 15]},
            sort_by="volume", sort_order="desc", limit=3,
            columns=["price_earnings_ttm", "volume"],
        ))
        payload = response.model_dump(mode="json").get("structured_content")
        if not isinstance(payload, dict) or payload.get("success") is not True:
            raise RuntimeError("Provider failure or unexpected envelope")
        data = payload.get("data")
        if not isinstance(data, dict) or data.get("ignored_filters"):
            raise RuntimeError("Unexpected data or ignored filters")
        rows = data.get("rows")
        if not isinstance(rows, list) or not rows:
            raise RuntimeError("No rows for semantic verification")
        for row in rows:
            value = row.get("price_earnings_ttm")
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or not 0 <= value <= 15):
                raise RuntimeError("Filter mismatch or missing value")
        print({"evaluated": len(rows), "totalCount": data.get("totalCount"),
               "coverage": "sample only"})

asyncio.run(asyncio.wait_for(main(), timeout=90))
```

例は静的構文・契約確認のみ。今回の実取得は同じRequestを既存Clientから呼ぶ調査用コードで行った。例の出力は集計のみで、利用者の完成Screeningの保存結果ではない。

## 静的検証と未実施範囲

4回帰ケース（プライムSMA25、PER、順位確定後1h RSI14、全米株無条件全件）をAIガイド・カタログ・実Schemaへ照合。JSON優先、元母集団/処理順保持、方式B検討、外部母集団の条件付き利用、失敗/部分取得の区別を維持。新しい代替提案規則は、元条件を保つ方式Bの検討後に最大3案、変更点と状態を示し、条件変更には承諾が必要とした。各AIの実際の生成・遵守を試験したものではない。

Windowsのapp.bat / setup.bat / scripts/setenv.bat / scripts/development/console.bat / scripts/setup-runtime.batの現行配置と起動手順を確認した。自作Pythonはsetenv後のEmbedded Pythonから起動し、screen/Job名には渡さない。

静的検証は35 Tool節・107引数行の必須性/型/enum/nullable/上限、カタログ32項目・6preset・17分類163列、相対リンク/アンカー276件、Pythonコードブロック2個の構文で合格。PER例は保存済み応答を現行ObservedReadResponseへ読み込み、ネットワーク呼出しを差し替えたオフライン実行でも3件評価に成功した。Windows asyncioの内部socketpairがsandbox内で停止するため中断し、sandbox外で再実行してexit 0を確認。追加のProvider Readは行っていない。

未実施：全市場・全列・全filter・全preset、全35 Toolの実行、プライム母集団の直接確定、直接SMA25/乖離率、OHLCVからの全プライム抽出、RSI14の定義一致、JPX取得、価格調整/確定足の完全検証。全米株無条件一括取得は過去2026-10-18の制約記録を維持し、今回は再取得していない。

文書のみのため全件pytest・Docker再buildは実施しない。production・Schema・CLI・BAT・認証・通信制御・依存関係・AI入口文書・既存設定に変更を加えない。既存の未追跡tradingview_container_test/は作業対象外。

## 配布方針

README2言語・利用者文書6ファイル（新規2を含む）を配布対象コミットとし、本記録・開発索引を別コミットにする。develop向けPRは1本。main反映が必要になった別の配布工程で、レビュー・merge後の実コミットを確認し、配布対象だけをcherry-pick -xする。develop全体をmainへmergeしない。

## PR #63・#65統合追記（2026-10-27）

上記は10/26時点の契約・実測記録として保持する。[PR #63](https://github.com/TakamKaji/tradingview_mcp_support/pull/63)はMerge Commit `0095ee99d427e7463a569eedf6386f4485ce2b7e`でdevelopへ反映した。配布対象04c8eac・開発専用d5d5125の履歴を保持している。

そのdevelopを[PR #65](https://github.com/TakamKaji/tradingview_mcp_support/pull/65)へ通常merge `b219917bf9ac2dc89648ca7bce64cd1960bb3b28`で統合し、開発索引の競合は両方の記録へのリンクを保持して解消した。73c411b・a0defe9を保持し、mainは変更しない。

統合後の[マニュアル](../user/OFFICIAL_MCP_MANUAL.md#get_ohlcv)は現行110引数（OHLCV7引数）へ更新した。date_from/date_to/format、rows5000/columns8000、両応答形式・カーソル保持・省略互換を記載。8000指定は実取得5本の既存Read結果に限る。上記の107引数・旧4引数やDiscovery差分は実装前の記録であり、現在の未対応を示さない。

新しいProvider Readは不要であり、[10/27監査の既存実機結果](MCP_PARITY_AUDIT_2026-10-27.md#少量read実機確認)を再利用する。統合後の検証・配布対象コミット・マージ結果はPR #65と下記監査の統合追記を参照する。
