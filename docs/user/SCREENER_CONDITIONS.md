# スクリーニング条件カタログ

調査基準日：**2026-10-26 JST**。機能全体は[公式MCP機能マニュアル](OFFICIAL_MCP_MANUAL.md)、JSON全項目は[Screening操作](SCREENING_MANUAL.md)、方式選択・代替提案の正本は[AIガイド](AI_JSON_GUIDE.md)を参照します。[公式Provider資料](https://www.tradingview.com/mcp/docs)・既存Schema・当日の小規模Readを照合しています。

## 状態と今回の確認範囲

| 状態 | 意味 |
| --- | --- |
| **公式仕様確認** | 公開ページに明記された引数/例。個別市場での成功を保証しない |
| **実機確認済み** | 既存Clientで取得し、試した範囲の条件適合を実値で確認。市場・日時・件数を併記する |
| **列取得のみ確認** | 列一覧に存在、または値取得を確認。filter対応は別。表で「一覧」「値」「応答項目」を区別する |
| **未確認** | 期間・市場・filter対応等の根拠不足。非対応の意味ではない |
| **非対応確認** | 指定した市場・キー・試験でProviderが無視/拒否したことを確認。別aliasや別方式まで不可能とはしない |

当日の実機は日本株の各3件を中心とする少量Readです。数値filterは**5種類を試し、3種類で適合、2種類で指定キーの無視を確認**しました。加えて米国preset 1種類、既知銘柄の単体/一括指標・テクニカル・日足を確認しました。母集団全件や全期間・全市場の検証ではありません。

`get_screener_columns(market="stock")`は**17分類・163列**を返しました。valuation 20列・technicals 26列をgroupで詳細取得し、SMA/EMA/primeをsearchしました。これは固定保証の件数ではありません。表の32項目は用途別の索引で、動的な全列を無差別に転記したものではありません。

## 市場・銘柄集合・時間足を先に固定する

- `run_screener.market`の公式例：`japan`、`america`、`uk`、`germany`、`india`、`crypto`、`forex`、`futures`、`bonds`、`cfd`。完全な対応市場一覧・組合せの固定enumは今回確認できていません。未知市場名を作りません。
- `symbol_types`は銘柄種別（公式例`["stock"]`）。株式/ETF等の種別と国・取引所・上場区分は別です。`get_screener_columns.market`は`stock/etf/crypto/bond/all`であり`japan`は渡しません。
- `symbolset`は明示集合。公式例`["SYML:SP;SPX"]`はS&P 500で、全米株ではありません。`filters.index`の指数指定と同じ意味になるかは個別に確認します。
- `market=japan`は東証プライムを意味しません。prime検索で該当列を発見できなかったことだけで、直接指定の不存在を断定しません。母集団の確定方法を既存Readから調べ、成立しなければ制約を報告します。外部一覧の取得・利用はユーザーの明示的な依頼・承諾後だけです。
- 日足/1h、指標期間、対象日、確定/進行中足を区別します。列説明にある時間足派生と実際のfilter対応は別です。今回`RSI|60`の値取得を確認しましたが、1h RSI14の期間同一性やfilter対応は未検証です。

## 主条件・取得項目の索引

「—」は未確認で、架空のfilter名や条件例を補いません。列とRead応答内の項目は明記して区別します。`[下限,上限]`のnullは片側制限なし、単位は項目ごとに確認してください。下表の**無視された指定は不合格例**であり、生成JSONへ採用する例ではありません。

| 条件・用途 | filter名 / 公式フィールド | 条件指定例 | 取得列・Read応答項目 | 市場・時間足/期間 | 検証状態 |
| --- | --- | --- | --- | --- | --- |
| 株価・終値 | filterは— | — | `close` | Japan、時点を別確認 | 列取得のみ確認（値、単体Read） |
| 騰落率 | filterは— | — | `change` | stock一覧、基準価格は要確認 | 列取得のみ確認（一覧） |
| 出来高 | 数値filterは— | 並替`sortBy="volume"` | `volume` | Japan、日足/時点を別確認 | 実機確認済み（3件の出来高降順のみ。数値filter未検証） |
| 時価総額 | filterは— | — | `market_cap_basic` | stock、通貨/単位を要確認 | 列取得のみ確認（一覧）、filter未確認 |
| PER | `pe` | `[0,15]` | `price_earnings_ttm` | Japan/stock、TTM列との値照合 | 公式仕様確認・実機確認済み（3件） |
| PBR | aliasは未確認。列名`price_book_fq`でのfilterは無視 | 不合格：`price_book_fq:[0,1]` | `price_book_fq` | Japan、FQ列 | 非対応確認（このfilterキー）。列値は一括Readで確認 |
| 予想配当利回り | `div_yield` | `[3,null]` | `dividends_yield` | Japan/stock、% | 公式仕様確認・実機確認済み（3件） |
| TTM配当利回り | aliasは未確認。列名filterは無視 | 不合格：`dividends_yield_ttm:[3,null]` | `dividends_yield_ttm` | stock一覧、今回3行は値null | 非対応確認（このfilterキー）。TTM条件全般の否定ではない |
| 売上高 | — | — | `total_revenue_fy` | stock一覧、FY | 列取得のみ確認（一覧） |
| 純利益 | — | — | `net_income_fy` | stock一覧、FY | 列取得のみ確認（一覧） |
| 売上成長率 | — | — | `total_revenue_YoYTTM` | stock一覧、YoY/TTM | 列取得のみ確認（一覧） |
| EPS成長率 | — | — | `earnings_per_share_diluted_YoYTTM` | stock一覧、希薄化/YoY/TTM | 列取得のみ確認（一覧） |
| ROE | — | — | `return_on_equity_ttm` | stock一覧、TTM | 列取得のみ確認（一覧） |
| 負債/資本 | — | — | `debt_to_equity_fq` | stock一覧、FQ | 列取得のみ確認（一覧） |
| 流動比率 | — | — | `current_ratio_fq` | stock一覧、FQ | 列取得のみ確認（一覧） |
| RSI | `rsi` | `[null,40]` | `RSI` | Japan、列説明は既定1D。期間14の同一性は未照合 | 公式仕様確認・実機確認済み（3件の閾値適合） |
| 1時間足RSI | 時間足filterは— | — | `RSI`の派生`RSI`＋区切り記号＋`60`（下記） | TSE:7203、1h派生列 | 列取得のみ確認（値）。期間/直接filterは未確認 |
| MACD | — | — | `MACD.macd` / `MACD.signal` | stock他、派生足は要個別確認 | macd値取得確認、signalは一覧variants確認。filter未確認 |
| ストキャスティクス | — | — | カタログ`Stoch`、technicals応答`oscillators.stoch_k/stoch_d` | 既知銘柄1D | 列一覧/Read応答項目のみ確認。`Stoch`をそのままfilterにしない |
| SMA20/50等 | — | — | technicals応答`moving_averages.sma20/sma50`等 | 既知銘柄1D | Read応答項目のみ確認。Screener列名ではない |
| SMA25 | — | — | 直接列・technicalsのSMA25は未確認 | 市場/足/期間を要確認 | 未確認。SMA検索不一致だけで非対応としない |
| SMA25乖離率 | — | — | 直接列は未確認。必要なら既存OHLCVでPython計算 | 確定日足25本と同じ基準日の終値 | 未確認（直接filter）。ローカル計算経路はAIガイド参照 |
| EMA50/200 | — | — | `EMA50` / `EMA200` | america、oversold_healthy応答 | 列取得のみ確認（値）。EMA検索だけでは発見できなかった |
| EMA乖離率 | — | — | `price_vs_ema50_pct` / `price_vs_ema200_pct` | 同上、% | 列取得のみ確認（応答の値）。直接filter未確認 |
| ボラティリティ | — | — | `Volatility.D` | TSE:7203単体Read | 列取得のみ確認（値）、計算基準/filterは未確認 |
| ATR系 | — | — | `ATRP` | stock他の列一覧 | 列取得のみ確認（一覧） |
| 高値安値関連 | — | — | `High.3M` / `Low.3M`、`pct_from_high_3m`等 | Screenerの追加応答項目 | 列取得のみ確認（応答に存在）。全てを指定列/filterとして検証していない |
| セクター | `sector`（文字列） | 値を調べて指定 | `sector` | stock/bond等の列説明に従う | 公式仕様確認、列一覧確認。今回filter値未検証 |
| 業種 | `industry`（文字列） | 値を調べて指定 | `industry`は公式の既定列例 | 対応市場/分類値を要確認 | 公式仕様確認、今回の個別適用は未確認 |
| 指数 | `index`（文字列） | `"S&P 500"` | 指数は母集団指定 | america、他指数は個別確認 | 公式仕様確認。過去2026-10-18にS&P 500の取得記録、今回未再試験 |
| 東証プライム区分 | — | 未確認キーを作らない | prime検索では発見できず | japanと区別 | 未確認。列検索の不一致を市場区分の非対応証拠にしない |
| アナリスト評価 | `analyst_rating`（文字列） | 許容値は要確認 | `AnalystRating` | stock一覧 | 公式仕様確認（filterキー）、列一覧確認。文字列条件と数値列を混同しない |

時間足列の区切り記号は縦棒（U+007C）です。今回値を確認した完全な表記：

```text
RSI|60
```

OHLCVを使うローカル計算では、[日付範囲・rows/columnsの契約](OFFICIAL_MCP_MANUAL.md#get_ohlcv)に従って実応答を解釈します。columnsの上限8000や日付指定対応は、確定足・価格調整・母集団全件の完全性を保証しません。以下の条件/filter検証は2026-10-26の記録を維持します。

列説明ではADX/AO/ATRP/BB/MACD/RSI/Stoch等に時間足接尾辞の案内があります。`1,5,15,30,60,120,240,1W,1M`等の表記はToolのinterval引数と別です。RSIの1h以外の各組合せやfilterへの転用は今回未検証です。TechRatingのvariantsは`TechRating_1m`〜`TechRating_1M`型で、別形式です。

## 公式Preset 6種類

指定位置はJSONの`filterPreset`、Python Requestでは`filter_preset`です。名前は公式/現行Schemaで確認済みですが、以下の目的の要約を完全な数式・固定閾値の定義と扱いません。市場・列・追加filterの組合せはProvider依存です。

| 正式値 | 探す用途の目安 | 現在の確認状態 |
| --- | --- | --- |
| `pullback_with_reversal` | 押し目から反転する候補 | 公式仕様確認。内部の正確な計算式/閾値、今回実行は未確認 |
| `breakout_with_volume` | 出来高を伴う上抜け候補 | 同上 |
| `oversold_healthy` | 売られ過ぎと健全性を組み合わせる候補 | 公式仕様確認・americaで3件の取得成功。全内部条件の意味的検証は未完了 |
| `earnings_runup` | 決算に向けた値動きの候補 | 公式仕様確認。今回実行は未確認 |
| `relative_strength` | 相対的な強さの候補 | 同上。RSIと同じ指標とは扱わない |
| `new_highs` | 高値更新の候補 | 同上。高値期間を推測して固定しない |

oversold_healthyの今回応答にRSI、EMA50/200、EMA乖離率等がありました。列探索のsearch=EMAはpremarketの5列だけを返したため、文字列検索だけでEMA関連機能がないと判断しません。search=SMA/primeは今回「一致する列なし」のProvider失敗応答であり、全指標/全母集団機能の非対応を実証するものではありません。

## 分類索引とDiscoveryの進め方

stock指定で観測した全17分類です。件数は基準日の列一覧の数で、列の値取得・filter可否・その市場の全銘柄への対応を保証しません。stock指定でもbonds/ETF関連の分類が現れたため、詳細のmarketsと実応答を確認します。

| group | 観測列数 | 主な探索用途 |
| --- | --- | --- |
| balance_sheet | 31 | 資産・負債・流動性 |
| bonds | 4 | 債券価格・クーポン等 |
| cash_flow | 3 | キャッシュフロー |
| crypto | 1 | 暗号資産関連分類 |
| dividends | 9 | 配当・継続性 |
| earnings_estimates | 2 | 予想EPS・売上 |
| etf | 1 | ETF関連 |
| identity | 4 | 国・セクター等 |
| income_statement | 19 | 売上・利益・成長率 |
| misc | 1 | その他の成長指標 |
| ownership_shares | 2 | 従業員・自社株買い関連 |
| performance | 4 | 時価総額派生・騰落・変動性 |
| price | 15 | 価格・騰落・時間外 |
| profitability | 14 | 利益率・効率性 |
| technicals | 26 | 指標・評価・時間外関連 |
| valuation | 20 | PER・PBR等の企業価値指標 |
| volume_liquidity | 7 | 出来高・売買代金・流動性 |

Pythonでは既存`GetScreenerColumnsRequest(market="stock")`で概要を読み、`group="valuation"`や`search="RSI"`等を追加して詳細を読みます。両方を常に全件取得せず、必要な分類・項目に絞ります。大きな全列一覧を文書へ固定転載せず、動的Discoveryでname・markets・variants・説明を再確認してください。

並替は`sort_by`/JSONの`sortBy`、`sort_order`/`sortOrder`を使います。今回実測したのはJapanのvolume降順のみです。任意の取得列がそのまま並替に使えると断定せず、昇降順・null・同順位・limitによる切捨てを確認します。

## filter適用を確かめる手順

1. 元の母集団・期間・足・単位・閾値を固定し、公式で確認したfilterか、列名の適用可否を試す調査なのかを区別する。未確認の調査キーを利用者の完成JSONへ採用しない。
2. 既存Client/Request/Governorで少数行を取得し、success/error、ignored_filters、partial/missing、返却件数とtotalCountを記録する。
3. 無視申告が空/未掲載でも成功の証明にせず、返却列の実値が閾値・単位・日時に一致するか確認する。候補抽出が真の該当を取りこぼさないことも別に検証する。
4. 不適合や無視された条件は標準JSON成功とせず、別aliasの公式根拠または方式Bの値取得/計算を調べる。条件変更は利用者の承諾なしに実行しない。

今回の少量試験：

| filter試験 | market / 件数 | 意味的確認 | 結果 |
| --- | --- | --- | --- |
| pe=[0,15] | japan/stock、3件 | 全値が0〜15、出来高降順 | 実機確認済み。総該当1904、全件取得ではない |
| div_yield=[3,null] | 同上 | 全値が3%以上、出来高降順 | 実機確認済み。総該当1554 |
| rsi=[null,40] | 同上 | 全値が40以下、出来高降順 | 実機確認済み。総該当1304。期間14の同一性は別途確認 |
| price_book_fq=[0,1] | 同上 | ignored_filtersにキー、返却値が1超 | このfilterキーは非対応確認。PBR列値は取得可能 |
| dividends_yield_ttm=[3,null] | 同上 | ignored_filtersにキー、返却値null | このfilterキーは非対応確認。別alias/別方式は未確認 |

取得日時は2026-10-26 23:16 JST頃、既存Windows Embedded Python・Client・保存済み認証を使用しました。件数・値は当日の観測で、固定値ではありません。応答は要求していないEMA等の追加項目も含んだため、標準Engineの正規化と必要列の意味を照合します。生の市場データ・認証情報を配布文書へ大量転載しません。

## AIへの提示と4回帰ケース

通常の依頼にこの全表を毎回表示しません。利用者が条件を尋ねた場合や変更が必要な場合だけ、関連項目と状態を簡潔に示します。元の条件を保てる方式Bを先に検討し、必要な代替条件・外部データ利用案は最大3件程度、変更点と制約を示して承諾後にだけ採用します。詳細規則は[AIガイド](AI_JSON_GUIDE.md)が正本です。

| ケース | カタログから選ぶ判断 |
| --- | --- |
| 東証プライム全体・SMA25乖離率+20% | プライム区分/直接SMA25は未確認。公式MCPの直接対応→既存Read→必要時のOHLCV計算を調査し、元条件が成立しなければ制約を説明。JPX自動取得・63銘柄等への無断変更や、小規模テストを全件成功とする判断は禁止 |
| 日本株PER15倍以下・予想配当利回り3%以上 | pe/div_yieldの検証範囲とPER下限・予想配当の基準を確認して標準JSONを優先 |
| 指定3銘柄のSMA25計算 | 指定母集団を保持し、必要なら既存MCPのOHLCVで方式Bの計算・検証。外部銘柄一覧は不要 |
| JPX公式一覧を明示的に許可 | 承諾範囲の外部利用を別拡張として行い、公式MCP経路と分離。基準日・対応付け・完全性を検証 |

[公式MCP機能マニュアル](OFFICIAL_MCP_MANUAL.md) / [Screening操作](SCREENING_MANUAL.md) / [利用者マニュアル](README.md)
