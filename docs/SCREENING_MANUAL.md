# Screeningと管理Watchlist

## Screening実行

リポジトリ直下から、Windowsでは `console.bat` を開いて実行します。

```text
python -m tradingview_screening screen sample_standard_screen
python -m tradingview_screening results latest sample_standard_screen
```

`screenings/<name>.json` を既存Pydantic modelで検証します。filtersはProvider形式を維持し、symbolや条件をAIが再解釈しません。結果はstdoutと `results/YYYY-MM-DD/` へ保存します。[結果契約](RESULTS.md) を参照してください。

## preset・symbolset・取得範囲

名前付き定義に `filterPreset` と `symbolset` を指定できます。`filterPreset` は公式の `pullback_with_reversal` / `breakout_with_volume` / `oversold_healthy` / `earnings_runup` / `relative_strength` / `new_highs` のいずれかです。`symbolset` は空でない文字列配列で、公式例は `["SYML:SP;SPX"]` です。指定された値をwrapperの `filter_preset` / `symbolset` へ渡します。

既存の数値filterは `[min, max]`、片側の `null` は上限または下限なしを表します。両側null、逆転範囲、非有限数、booleanは拒否します。`index` / `sector` / `industry` / `analyst_rating` は空でない文字列を使います。独自演算子は追加しません。filterとpresetとsymbolsetは併用可能ですが、意味の組合せはProviderが決めます。

空の `filters` は既存定義との互換性のため許容します。ただし条件を全省略した要求は現在のProviderが業務エラーとして拒否します。カラムに存在する名前がfilterとしても動くとは限りません。実測では `dividends_yield_ttm` filterが無視されたため、公開例は公式alias `pe` / `div_yield` を使います。配当条件は予想配当利回りでありTTM配当利回りとは区別します。

`totalCount` は要求条件に対するProviderの総件数、`returnedCount` は実際の行数です。上位5件の取得を全件取得とは扱いません。`completeCoverage=true` はその要求条件の範囲で行数・一意symbol数がtotalCountに一致した意味です。S&P 500の全件を取得しても全米株Universeの保証にはなりません。[件数契約](RESULTS.md)も参照してください。

## 公開read-onlyサンプル

以下はすべて `limit=5`、Watchlist disabledです。対応Jobは `enabled=false` / `save=true` / `watchlistSync=false` で、Schedulerへ自動登録されません。手動実行は結果JSONを保存します。

| 定義 | 条件 | 手動Job |
| --- | --- | --- |
| public_japan_value | japan、PER 0〜15、予想配当利回り3%以上、出来高降順 | public_japan_value_daily |
| public_sp500 | america、index=S&P 500、出来高降順 | public_sp500_daily |
| public_oversold_healthy | america、公式preset、RSI/EMA/EMA乖離率 | public_oversold_healthy_daily |
| public_sp500_symbolset | america、SYML:SP;SPX、出来高降順 | public_sp500_symbolset_daily |

```bat
app.bat run public_japan_value_daily
app.bat run public_sp500_daily
app.bat run public_oversold_healthy_daily
app.bat run public_sp500_symbolset_daily
```

EMA列はpresetの実応答で確認したProvider計算値です。PublicコアでOHLCVから再計算しません。[2026-10-18検証記録](MCP_VERIFICATION_2026-10-18.md)に範囲と制約を記録しています。

## Watchlist設定（同期API）

```json
{
  "watchlist": {
    "enabled": true,
    "name": "[Auto] Sample Standard Screen"
  }
}
```

未指定またはenabled=falseなら同期APIはWriteせず、successとskippedを返します。enabled=trueではnameが必須です。nameは新規作成名・診断用expectedNameであり、同名の既存Watchlistを採用するためには使いません。

`screen` コマンドはPhase 7でもWatchlistを同期しません。同期は次のPython APIを明示的に呼びます。

## Python API

次の例は保存済みの最新成功結果を使い、アプリ管理Watchlistへ実際にWriteします。最新結果の日付と内容を確認してから実行してください。

```python
import asyncio
import json
from pathlib import Path

from tradingview_screening.integrations.tradingview.client import TradingViewClient
from tradingview_screening.screening.results import latest_result
from tradingview_screening.screening.validators import load_screening_by_name
from tradingview_screening.screening.watchlist_sync import sync_screening_watchlist

async def main():
    root = Path.cwd()
    definition = load_screening_by_name("sample_standard_screen", root)
    result = latest_result(root, definition.name)
    async with TradingViewClient() as client:
        synced = await sync_screening_watchlist(definition, result, client, root)
    print(json.dumps(synced, ensure_ascii=True))

asyncio.run(main())
```

取得直後に同期する場合も既存 `screening.engine.run_screening()` が返した正規化済み結果を渡します。Engineの複製やMCP raw responseの受渡しは不要です。

## 入力と失敗

- success Envelopeだけを受け付けます。failed、partial、errors付き、Screening名不一致、件数不整合は拒否します。
- symbolはEXCHANGE:TICKER形式の非空文字列。1件でも不正ならWrite前に全体を拒否します。文字列は変換せず、重複と順序差だけを除きます。
- 正常な0件結果は、保存済み管理IDの銘柄を全removeします。Provider失敗を0件に読み替えることはありません。
- 差分Write前の既知の失敗はAppErrorとして伝播します。差分Write途中の失敗はfailed/partialの同期結果で返し、確認済みのadded/removedだけを記録します。
- Writeを自動再送・rollbackしません。再実行時は現在の管理WatchlistをReadして差分を計算し直します。

mappingを手で既存Watchlist IDに置換してownershipを移す運用は行わないでください。詳細は [WATCHLIST_SYNC.md](WATCHLIST_SYNC.md) を参照してください。

Phase 8では`app.bat run <job>`から取得・任意保存・任意Watchlist同期をまとめて呼べます。`screen`単体は引き続きReadと保存のみです。`jobs list`とSchedulerは[Schedule Manual](SCHEDULE_MANUAL.md)を参照してください。
