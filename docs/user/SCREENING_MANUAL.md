# Screeningを実行する

## Screening実行

セットアップ後、展開フォルダでコマンドプロンプトを開き、次を実行します。PowerShellでは各行の先頭を `.\app.bat` に置き換えます。

```text
app.bat screen sample_standard_screen
app.bat results latest sample_standard_screen
```

`screenings/<name>.json` に保存した条件を検証して実行します。条件や銘柄名をAIが再解釈する処理は行いません。結果は画面へJSONで返し、`results/YYYY-MM-DD/` へ保存します。読み方は[結果マニュアル](RESULTS.md)を参照してください。

## preset・symbolset・取得範囲

名前付き定義に `filterPreset` と `symbolset` を指定できます。`filterPreset` は公式の `pullback_with_reversal` / `breakout_with_volume` / `oversold_healthy` / `earnings_runup` / `relative_strength` / `new_highs` のいずれかです。`symbolset` は対象銘柄集合を指定する空でない文字列配列で、公式例は `["SYML:SP;SPX"]` です。

既存の数値filterは `[min, max]`、片側の `null` は上限または下限なしを表します。両側null、逆転範囲、非有限数、booleanは拒否します。`index` / `sector` / `industry` / `analyst_rating` は空でない文字列を使います。独自演算子は追加しません。filterとpresetとsymbolsetは併用可能ですが、意味の組合せはProviderが決めます。

空の `filters` は既存定義との互換性のため許容します。ただし条件を全省略した要求は現在のProviderが業務エラーとして拒否します。カラムに存在する名前がfilterとしても動くとは限りません。実測では `dividends_yield_ttm` filterが無視されたため、公開例は公式alias `pe` / `div_yield` を使います。配当条件は予想配当利回りでありTTM配当利回りとは区別します。

`totalCount` は要求条件に対するProviderの総件数、`returnedCount` は実際の行数です。上位5件の取得を全件取得とは扱いません。`completeCoverage=true` はその要求条件の範囲で行数・重複しない銘柄数がtotalCountに一致した意味です。S&P 500の全件を取得しても全米株全体の保証にはなりません。[件数の読み方](RESULTS.md#履歴を見る)も参照してください。

## 公式MCP Beta版のスクリーニング制限（2026-10-18実機確認）

TradingView公式MCPはBeta版です。利用できる引数や応答は、今後のProvider更新で変更される可能性があります。以下は **2026年10月18日、MCP server 1.30.0 / protocol 2025-11-25** の実環境で確認した制約です。

| 操作 | 現在の対応状況 |
| --- | --- |
| `filters` / `filter_preset` / `symbolset` による条件付きScreening | 利用可能。条件と銘柄によってProviderの返却件数・成功可否は変わります |
| `america` / `stock` で条件を一切指定しない全米株Screening | **TradingView公式MCP Providerが拒否**。OAuthや本アプリの接続障害ではありません |
| 一度に取得できる行数 | `run_screener.limit` は最大1000行（当時の公式Tool定義） |
| 1000行を超える結果の全件取得 | 現行Tool schemaには `offset` / `page` / `cursor` がなく、全件取得方法は確認できていません |
| 全米株全体のセクター別平均騰落率 | **本アプリの現行β版では未対応**。完全に取得できていないデータを全米株平均と表示しません |

利用可能な例として、`filters.index = "S&P 500"` を指定した検証では、該当503件を重複なしですべて取得し、TradingViewのsector分類20件について単純平均騰落率と順位を計算し、JSON保存・読み戻しまで確認できました。ただし、これは**S&P 500に限定した検証結果**であり、全米株全体ではありません。現行mainには、この限定集計を製品Jobとして提供する機能は含めていません。

条件なしScreeningが拒否された場合、条件を指定した別Screeningを利用してください。単に取得上限1000件まで成功したからといって `completeCoverage=true` や全米株取得成功とは扱いません。未確認のページング引数や非公式APIによる回避は提供しません。

この制限は**検証日時点の公式MCP Beta版についての実測**であり、TradingViewが将来も対応しないという意味ではありません。詳細は[Phase 9の実機検証](https://github.com/TakamKaji/tradingview_mcp_support/issues/18#issuecomment-6250858944)を参照してください。

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

EMA列はpresetの実応答で確認したProvider計算値です。PublicコアでOHLCVから再計算しません。[2026-10-18検証記録](https://github.com/TakamKaji/tradingview_mcp_support/blob/develop/docs/archive/MCP_VERIFICATION_2026-10-18.md)に範囲と制約を記録しています。


## 自分の条件を追加する

1. [公開例の定義](../../screenings/public_japan_value.json)を `screenings/` 内へコピーし、ファイル名と内部の `name` を同じ新しい名前にします（英数字・`_`・`-`を使用）。
2. market、filters、sortBy、sortOrder、limit、columnsを編集します。通常の数値条件は `[下限, 上限]`、片側の `null` は制限なしです。limitは1〜1000で、取得列とfilterの対応はProviderによって異なります。
3. 初回はWatchlistを無効のままにし、`app.bat screen 名前` で取得・保存結果を確認します。未知キーや不正な定義はエラーになります。

`screen` はWatchlist設定が有効でも同期せず、取得とローカル保存だけを行います。Jobとして使うには[Schedulerマニュアル](SCHEDULE_MANUAL.md)、同期する場合は[Watchlistマニュアル](WATCHLIST_SYNC.md)へ進んでください。内部SchemaとPython APIは[開発資料](https://github.com/TakamKaji/tradingview_mcp_support/blob/develop/docs/development/SCREENING_API.md)に分離しています。

[利用者マニュアル一覧](README.md)
