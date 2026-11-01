# 公式TradingView MCP 実機観測・配布版での安全な利用（2026-10-27）

この文書は**公式MCPへ直接接続した計246 Read**の調査結果のうち、配布用`main`で誤動作を避けるための要点です。調査は**本リポジトリのラッパーの受入テストではありません**。利用時には、ご自身の認証プランと実行環境でProviderの現在の挙動を再確認し、`success`に加えて条件適用・行数・欠損を確認します。

## 銘柄集合とSMA25

- 公式MCPの`run_screener`直接Readで、日経225 `symbolset:["SYML:TVC;NI225"]`、stock指定が**225/225行**、重複0。S&P 500は503/503、NASDAQ 100は型指定なし101/101。**NASDAQ 100で`symbol_types:["stock"]`を加えると98/98となり、DR型のARM・ASML・PDDが脱落しました**。元の指数算出元との独立照合は未実施です。
- 日経225の`filters.index:"nikkei 225"`は0件、TOPIXのindex文字列指定は拒否。**動作確認済みsymbolsetと曖昧なindex名は代用不可**。
- `close`、`SMA25`は直接取得成功例があります。ただし取得列とfilterは別です。公式MCPでは`RSI7`と既定MACDのfilter成功、`SMA13`や`EMA25`等が`ignored_filters`になる例があります。**`price_vs_sma25_pct`を有効filterとみなさない**。
- 日経225から**終値/SMA25の乖離率+20%以上**を抽出する場合、225行を取得し、全行に`close`と`SMA25`が存在するか確認後、`(close/SMA25-1)*100`を計算。日足価格とSMAの基準時点、分割調整、null、0除算、確定足を確認。単一JSONのProvider filterだけで+20%以上を表現できると確認していないので、**標準Screening JSONで全件取得→ローカル後処理**、または既存`TradingViewClient`経由の小さなPython処理を選択。新たなMCP通信・OAuthを作り直さない。
- 東証プライムについては`market:japan`/`exchange:TSE`とPrime上場区分を同一視しない。Prime所属候補6列がnull、`market_segment:"Prime"`は無視され、**Prime全件母集団は未検証**。日経225やTOPIX、東証全件、先頭1000行をPrime全件と称しない。完全な母集団が確定できなければ範囲・未達理由を報告。

## 期間・時間足とOHLCV

- `RSI7/9/21`、`SMA13/21/25`、`EMA13/21/25`には直接取得成功例あり。しかし`RSI24/48/96/192`、`SMA48/96/192`、`EMA48/96/192`は試した日本・米国株でnull。**任意の整数期間が使えるとは限らない**。既定`RSI`が数値でも明示`RSI14`はnullだった例あり。
- `|60`/`|240`/`|1W`の取得成功例はあるが、これらをScreenerのfilterに流用できる保証はなく、時間足付きRSIは無視された例があります。
- 日足RSI7・既定RSI・SMA13・EMA13/25・MACDはToyota/Appleで600本から再計算して一致。**Toyotaの過去1h/4hバーではOHLCVのrows/columnsにclose・volume差**があり、一部修正した診断計算で指標が一致。Appleの1h/4hは両format一致でも直接指標差が残り、原因未確定。片方のformatを無条件に正本としない。
- ローカルの長期RSI48/96/192は600本でもseedの影響が残り得ます。必要履歴を増やして収束を検査します。1hのRFC3339`date_to`より後のバーが返った例があり、`t`を検証。取得成功を厳密な日付窓・確定足の保証としません。

## 財務・予想・カレンダー

- `get_forecasts`の日本株7銘柄で**JPYラベルなのに円建てraw値と異なる**例。4社20/20と追加3社11/15、計31/35項目で`raw × FX_IDC:JPYUSD`の対象期末候補の日足終値がPython floatで一致。次FYのEPS/売上は7社14/14で直近実績FY末、EPS TTMは7社7/7で実績FQ末の係数と一致。イオンとファーストリテイリングの、次のFQに関する残り4項目は基準日未確定（未来候補で照合不可）。
- **円建ての予想PER・成長率・目標株価へ`get_forecasts`のJPYラベル値を無検証で使用しない**。直近3月決算会社の固定係数を他社に当てると12/15項目が不一致。固定レートで自動補正しない。内部の通貨変換手順と会計期間の選択は未証明。日立のTradingView画面EPS 176.99 JPYはraw基本EPS TTM 176.9908の丸めと一致した例です。
- 財務データで、サフィックスなしの`net_income`が`period:ttm`指定でもFY値を返した例や、`eps`と履歴EPSで基本/希薄化が異なる例あり。**返却された値のsuffix・通貨・会計期末を照合**。
- 日本株の`get_earnings_calendar`0件でも、別のraw列に指定期間内の次回予定日があった例あり。配当はmarketモードで取得できる銘柄がsymbolsモードで0件になる例あり。0件を「発表なし」「無配」と断定しない。
- `get_screener_columns`の検索で0件でも実列Readが成功する例あり。Discovery・列Read・filter適用・単位の正当性を個別に検証します。

## 実行安全性と受入根拠

1. README→[AI JSONガイド](AI_JSON_GUIDE.md)→実際の[Screening Schema](../../src/tradingview_screening/screening/schema.py)、[公式MCP Request](../../src/tradingview_screening/integrations/tradingview/schemas.py)を読んで方式選択。
2. `run_screener`のProvider成功、`ignored_filters`、`totalCount`、`returnedCount`、`completeCoverage`、重複・nullを確認し、結果の時点・未評価件数を明示。
3. `app.bat screen <name>`はTradingViewからのデータ読み取り（Read）とローカル保存。`results latest <name>`は**古い成功結果の可能性**もあるので作成日時を確認。`watchlistSync`、Alert Write、`schedule apply/remove`は明示指示なしに実行しない。
4. `get_forecasts`、`get_ohlcv`等はラッパーのPython Readメソッドに対応していても専用CLI/Jobがあるとは限らない。CLIがないことをProvider非対応と混同しない。

**再現可能な取得条件・出力・失敗分類と実機受入の手順：** [自然言語スクリーニング受入](NATURAL_LANGUAGE_ACCEPTANCE.md)。この文書は2026-10-27の公式MCPへの直接Readによる調査結果の要約です。配布ZIPには生の調査資料を含めません。過去の観測結果と現在のProvider挙動、本ラッパー経由の動作確認は区別し、上記の未検証事項を確認済みとは扱わないでください。
