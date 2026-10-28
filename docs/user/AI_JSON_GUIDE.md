# AIによるScreening生成ガイド：標準JSONと高度なPython処理

この文書は**Gemini CLI・Codex・Claude Code・ChatGPT共通の作成・実行ガイド**です。**単一Screeningで表現できれば方式A（JSON）を必ず優先し、表現できない処理だけ方式B（Python）を選びます。** 日本語を正本とし、末尾に英語の要点を載せています。標準利用ではCodex・Git・ホストへのPython導入は必須ではありません。高度なPython処理には、ソースを編集・検証できる実行環境が必要です。

## AIが確認するファイル（この順）

1. [README](../../README.md)、次に[このガイド](AI_JSON_GUIDE.md)、[機能の対応範囲](FEATURES.md)
2. [Screeningの全項目・条件・制約](SCREENING_MANUAL.md)
3. Jobが必要なら[Jobの全項目・時刻・副作用](SCHEDULE_MANUAL.md)
4. 実際のサンプル：[Screening](../../screenings/public_japan_value.json)・[読み取り専用Job](../../jobs/public_sample_screen_daily.json)
5. 実際の[Screening Schema](../../src/tradingview_screening/screening/schema.py)・[Job Schema](../../src/tradingview_screening/jobs/schema.py)、[公式Providerの資料](https://www.tradingview.com/mcp/docs)・[型付きRequest](../../src/tradingview_screening/integrations/tradingview/schemas.py)

**必ず実際のファイルを読んでから作成してください。** 公開URLでもAIの閲覧機能やアクセス権によっては本文を読めません。読めないAIは閲覧したふりをせず、上記資料の添付・本文の提供を求めてください。Privateの間は通常の公開URLでは閲覧できません。新しいfilter・列・市場等はProviderの対応を確認し、Schemaが文字列を受理するだけで対応済みとしないでください。

## 2026-10-27公式MCP実測を踏まえた追加判定（配布版）

最新の[公式MCP Read能力・制約の要点](PROVIDER_VERIFICATION.md)は必ず確認してください。**公式MCPに246回直接Readした調査と、この配布版ラッパーの実行成功は別**です。

- **日経225構成銘柄**：公式MCP直接観測で`symbolset:["SYML:TVC;NI225"]`の225/225行を取得。全件を対象に`close`と`SMA25`を取得後、乖離率`(close/SMA25-1)*100`をローカルで評価する方法が候補です。未検証の`price_vs_sma25_pct`や日経225の文字列index filterで代用しない。Providerの今回の全件取得を、本ラッパー経由の新規受入成功とは呼ばない。
- **指数型指定**：NASDAQ 100で型省略101/101件、stock限定98/98件（ARM・ASML・PDDは`dr`型）。指数全構成銘柄に`symbolTypes:["stock"]`を自動追加しない。
- **東証プライム**：Prime所属とPrime全件の母集団は未確定。`market:japan`・TOPIX・先頭1,000銘柄への無断代用は禁止。完全性を保証できない場合、未達として停止・報告。
- **標準指標**：`SMA25`の直接値取得成功例はある一方、任意期間のRSI/SMA/EMAは不保証。列が存在してもfilterに通るとは限らず、`ignored_filters`があれば成功扱いしない。OHLCVで再計算する場合はformat・時間足・バーの確定性・履歴長を検証する。
- **財務予想**：日本株`get_forecasts`の予想EPS等は、JPYラベルのままraw値にJPYUSD終値を掛けた値と一致する例が7社あります。JPY単位として予想PER計算しない。固定換算係数を自動補正に利用しない。

初見エージェントの受入方法は[自然言語スクリーニング受入](NATURAL_LANGUAGE_ACCEPTANCE.md)。ファイル生成だけでなく、実行ログ・母集団の証拠・保存結果で合否を決めます。

## AIによる方式選択フロー

1. **希望を整理する。** 市場・銘柄母集団、条件、処理順、ランキングと件数、時間足・指標期間、取得列、保存、Jobの要否を確認する。PERの下限や利回りの予想/TTMなど、結果を変える曖昧さは説明・確認する。
2. **既存の標準Screening JSON・CLIを最優先する。** 上記Schema・公式Provider対応項目・`screenings/*.json`の同梱例と照合し、方式Aと`app.bat screen <name>`の既存手順を使う。Jobが求められた場合だけ`jobs/*.json`も作る。簡単な条件のたびにPython・BAT・独自実行環境を増やさない。
3. **標準機能で不足する処理だけ方式Bとし、既存ラッパーを再利用する。** 標準JSONで必要データを取得できるなら取得はJSON・CLIに任せ、Pythonは乖離率計算など必要な後処理だけに限定する。JSONで取得を表現できない場合は、製品の`TradingViewClient`等を使い、Pythonが必要な理由を説明する。既存認証・`RequestGovernor`・適合する保存機構を不必要に再実装しない。
4. **要求条件・母集団を確定できなければ停止する。** Providerの機能・全件取得可否を確認できなければ、未対応と未確認を区別し、理由を`BLOCKED`（未実行・続行不可）または`PARTIAL`（一部のみ取得・評価済み）として報告する。対象銘柄や条件を勝手に縮小・変更せず、存在しないfilter・APIを創作しない。Pythonへの変更で取得保証は増えない。Prime所属などの過去の未確認事項を永久に非対応とせず、公式MCPに正確な機能が提供された場合は既存ラッパー経由の実測・検証を優先する。
5. **外部データソースは代替案として提示し、明示的な選択・承認を待つ。** JPX公式上場銘柄一覧などを新たな入力ソースにする場合、提示段階では取得・導入も独自の外部母集団構築も実行しない。利用者がその方法を明示的に選択・承認した場合に限り実施する。利用者が対象の外部ファイルを提供した場合は、その利用指示の範囲内で使用できる。**「このツールを使ってスクリーニングしてください」だけでは外部母集団の新規取得・導入を承認されたと解釈しない。** 法的・技術的に利用可能、または検証済みというだけでは承認の代わりにならない。公式MCPの仕様確認・ドキュメント調査のためのWebアクセスは、新たな入力ソースの採用とは区別する。
6. **保存・ローカル検証・実取得・Writeを分ける。** ファイル作成だけの依頼でTradingViewへ接続しない。利用者の明示依頼なしにTradingViewへの実書き込みやScheduler登録・削除を行わない。

| 希望 | 選択 | 成果物・理由 |
| --- | --- | --- |
| 対応済みの市場・filter・sort・limit・columns、任意のsymbolset・preset | **A：標準JSON** | 単一Screeningで表現可能。Screening JSON、必要な場合だけJob JSON |
| 複数段階の抽出、ランキング確定後の別時間足判定、利用者が明示的に選択・承認した外部母集団との照合が必要 | **B：複合Python** | 標準JSONで取得できる部分は再利用し、不足する段階・結合・後段判定だけPythonと必要設定・依存・起動手順を用意 |
| Provider対応や取得の完全性を確認できない | **制約を報告** | 条件や母集団を黙って変更しない。Pythonでも取得保証は増えない |

### 母集団が確定できない場合の初回報告

指定母集団の完全性を確認できない場合、元の全件依頼は`BLOCKED`と報告し、未実行・未評価・該当0件を区別します。一部を取得・評価済みなら、その部分の`PARTIAL`と実際の範囲を併記します。**利用者の追加質問を待たず、初回のBLOCKED報告に次の代替候補を含めます。**

- 既存の公式MCPの取得記録と[製品資料](PROVIDER_VERIFICATION.md)から、全件取得実績を確認できる代替母集団を探す。元の依頼に近い市場・対象を優先し、通常1〜3件程度を提示する。国内の適切な候補がある場合、S&P 500・NASDAQ 100など市場が異なる候補を優先的に列挙する必要はない。取得実績のある候補が見つからなければ、その旨を伝え、候補を創作しない。
- 各候補には、元の母集団との相違、取得実績の出典・確認日・件数、データの基準日・網羅性、現在未確認の事項を簡潔に添える。不明な基準日は不明とし、**過去の取得成功を現在の取得保証と表現しない**。公式MCP直接Readの実績と本ラッパーでの実行実績も区別する。
- 例えば東証プライム全件が未確定なら、2026-10-27の製品資料に公式MCP直接Readで225/225件の取得実績がある日経225を候補にできる。ただしPrime全体とは異なる指数母集団であり、指数算出元との独立照合は未実施、今回の構成・基準日・網羅性・必要列とラッパー経由の取得は選択後に再確認が必要と説明する。
- **候補の提示は母集団変更・実行の承認ではない。利用者が明示的に選択するまで、代替母集団の取得・スクリーニングを実行しない。** JPX一覧など外部データの新規採用は、上記方式選択フロー第5項に従い、取得・導入・母集団構築前の明示承認を必要とする。

### 判定例（条件固有のファイルは同梱しない）

**ケースA：「日本株でPER15倍以下、配当利回り3%以上を出来高順で20件取得する」→ 方式A。** `market=japan`、`pe`・`div_yield`、`sortBy=volume`、`sortOrder=desc`、`limit=20`で表現できる。同梱例の`pe=[0,15]`は負のPERを除外し、`div_yield=[3,null]`は**予想配当利回り**を使う。PERの上限だけなら`[null,15]`との違いを説明し、利回りの基準も確認する。TTMを求められた場合、未確認のfilterへ置き換えない。Jobの希望がなければScreening JSONだけを提供する。

**ケースB：「グロース市場全体を対象に日足出来高上位100件を確定してから、1時間足RSI14が40以下の銘柄を抽出する」→ 方式B。** 「母集団を確認 → 日足出来高で順位確定 → その100件だけに1時間足RSI14の判定 → 保存」という順序が必要。現行の単一Screening JSONには段階や独立した時間足の後段判定を表す項目がない。Job JSONも単一のScreening参照でこの順序を追加できない。

最初からRSI条件を併用して取得すると、**RSI条件を満たす集合の出来高上位100件**になり、依頼と異なる。日本株の先頭1000件を取ってからグロース市場と照合しても、市場全体の上位100件とは保証できない。母集団、日足出来高、1時間足RSI14の取得方法・完全性を確認してから実装する。この2例は方式選択の説明であり、実取得の成功を示すものではない。

## 母集団・完全性・テクニカル指標の検証契約

「市場」「取引所」「上場区分」「全件」「ランキング」と「フィルタ適用順」を別々に固定します。`market=japan`は東証プライムの指定ではありません。出来高上位100件、手書きの代表銘柄一覧、先頭1000件を全上場銘柄の代わりにしません。Provider対応は[公式資料](https://www.tradingview.com/mcp/docs)、型付きRequest、必要なら既存Clientの`get_screener_columns`によるReadで確認します。列の存在だけでは、その市場でのフィルタ対応や期間・時間足まで保証しません。

- 対象母集団件数、評価済件数、未評価件数、失敗件数、完全性、対象時点を報告する。総件数不明は「不明」とし、未評価0とはしない。失敗件数は未評価のうち取得・計算等が失敗した件数として示し、二重加算しない。該当0件は必要な全対象を正常に評価できた場合にだけ結論とする。
- 標準結果の`totalCount`は**その問合せ条件**の総件数、`returnedCount`は取得行数。`completeCoverage=true`でも別途確認していない上場母集団の完全性は示さない。現行Engineは`status=success`でも`completeCoverage=false`を返し得るため、成功ステータスだけで全件取得と説明しない。標準JSONにない評価件数等は検証報告で補い、結果Schemaを勝手に追加・変更しない。
- `RunScreenerRequest`は最大1000行で、全件列挙用のoffset/page引数はない。`get_news`のページングをScreenerへ転用しない。全件を保証できない時は制約を明示し、母集団・条件を緩和せず完全取得の成功報告を止める。
- 25日SMAは、同じ基準日の**確定日足の終値25本**で計算可能か確認する。OHLCVを使う場合は`interval="1D"`で、生の足が必要なため`summary=false`とし、進行中足の除外後にも25本確保する。日時を解釈して昇順に整え、重複、非数値・欠損、取引日の抜け、株式分割等の価格調整の整合を検証する。休日を欠損扱いせず、25暦日や直近25行というだけで25取引日とみなさない。25本未満・日付不明・未確定足混在を無言でスキップしない。
- 基準価格を同じ確定日の終値`C(t)`とするなら、`SMA25(t)=直近25確定日足終値の平均`、`乖離率=(C(t)/SMA25(t)-1)*100`と示す。SMAが0・欠損なら評価不能。未指定の「20%以上」は通常**+20%以上**と解釈して報告し、絶対値20%以上（下方乖離を含む）へ変えない。進行中の現在値を使う依頼ならSMAとの時点差と計算基準を明示する。
- 同じ期間・時間足・価格基準の正しいProvider指標を直接取得できれば再計算を避ける。SMA25、RSI14の対応をラッパー名から推定せず、未確認なら未確認とする。Publicコアに新しい指標計算を追加しない。

## Windowsの起動契約

正式な利用者入口は[setup.bat](../../setup.bat)、[app.bat](../../app.bat)、[export-results.bat](../../export-results.bat)。内部BATは[scripts/setenv.bat](../../scripts/setenv.bat)と[scripts/setup-runtime.bat](../../scripts/setup-runtime.bat)です。旧ルート直下の`setenv.bat`を呼ぶ生成物は不合格です。条件ごとの新規BATを安易に作らず、通常は既存`app.bat`を使います。

複合Pythonに実行環境の設定が必要な場合だけ、プロジェクトルートのコマンドプロンプトで`call scripts\setenv.bat`後、`"%PYTHON_EXECUTABLE%" <拡張スクリプトのパス>`を使います。BAT内の相対パスはBATの保存場所から解決するため、場所を確認せず`%~dp0setenv.bat`を生成しません。PowerShellからBATを単独実行しても親PowerShellへ環境変数は引き継がれません。同じcmdプロセスで設定とPython実行を行ってください。

Embedded PythonとホストPythonの`site-packages`を`sys.path`で混在させない。`PYTHONHOME`/`PYTHONPATH`のクリアは既存起動プロセス内に限定し、OSのPATH・レジストリを恒久変更しない。`USERPROFILE`・`HOME`・`APPDATA`等をプロジェクト配下へ置換せず、OAuth・Credential Managerは通常のWindowsユーザー環境を保ちます。

## 「作成して実行」の完了契約

1. 方式・データ取得可否・実行環境・接続・Read権限を確認する。依頼されたTradingView Readとローカル結果保存はその実行範囲に含む。新規認証や追加権限が必要なら環境上の制約を説明し、認証情報削除で解決しようとしない。
2. 実行前の時刻と既存最新結果を控え、Read-onlyの`app.bat screen <name>`等を実行する。Jobの場合は実際の参照定義と`watchlistSync`等を確認し、暗黙のWriteがあれば実行しない。
3. 実際のstdout、stderr、exit codeを確認する。exit 0だけで完了とせず、`status`・`errors`・coverageを調べる。診断ログの秘密値は報告しない。
4. 新しい保存ファイルの実在、内容、`executedAt`、Screening名、条件のfingerprint、今回の実行との対応を照合する。`results latest`は過去の成功結果を返し得るため、古いファイルを今回の成功証跡にしない。実行失敗と過去結果は分けて報告する。
5. **成功・部分成功・失敗・未実行**を区別する。全件依頼で網羅性を証明できない場合は完全成功にしない。独自Pythonの結果は標準Screening形式・履歴比較への適合を確認できる場合だけ互換と説明する。

報告項目：方式（JSON/Python）と理由、実行コマンド・作業場所、元の母集団範囲、対象/評価済/未評価/失敗件数、coverage、閾値・方向、基準日時と実行日時、exit code・エラー、今回の保存先、状態。実行不能なら再現コマンドと実際に確認できたエラーまたは不足条件を示す。ファイル保存やSchema検証だけを実行成功としません。

Watchlist更新、Alert Write、Scheduler登録・削除、認証情報削除には**個別の明示依頼**が必要です。「スクリーニングして実行」だけでは許可されません。結果JSONが正本で、HTML/CSVは必要時に既存exportを使います。

## 自然言語の回帰ケースと不合格例

まず「このフォルダの使い方を理解して」、次に「このツールを使って東証プライムに上場している企業の中から25日移動平均線との乖離率が20％以上の銘柄をスクリーニングするスクリプトを作成し実行してください。」と依頼された場合も、README→本ガイド→実Schema・サンプル・BATを確認し、次の判断を行います。利用可能なら正しい方式で実行証跡まで検証し、不可なら不足する母集団・指標・接続の根拠を示して未実行/失敗と報告します。「スクリプト」という語だけでPython/BATを選びません。

| 入力ケース | 期待判断 | 不合格例 |
| --- | --- | --- |
| 東証プライム全体、SMA25乖離率+20%以上 | プライム全母集団と対象時点を保証し、Providerの市場区分・SMA25/乖離率対応を確認。標準JSONを優先し、不足する処理だけ既存ラッパーを利用。保証不能なら停止し、外部データは上記フローに従い代替案として提示 | `limit=100`の日本株出来高順＋手書き代表銘柄を全プライムとする。未承認のJPX一覧取得・外部母集団構築。OHLCV失敗/25本未満を除いてsuccess、未実行で完了宣言 |
| 日本株PER 0〜15、出来高順20件 | 同梱例とProvider対応を照合し標準JSONを優先。取得列とfilterを混同せず、20件のランキングとして報告 | 不要なPython/BAT、新規API、Schemaに通るだけの未知filter、上位20件を日本株全件とする |
| 出来高上位100件を確定後、1h RSI14で判定 | 元の市場母集団→日足出来高の順位確定→100件のみ1h RSI14→保存の順を維持。単一JSONで表せないためPython候補だが、RSIの期間/時間足・取得可否を先に確認 | RSIで先にフィルタしてから上位100件、先頭1000件を市場全体とする、日足RSIで代用 |
| 全米株を条件なしで全件取得 | 現行Provider制約で未対応と報告。最大1000件・ページング未対応も照合し、条件を変えて実行しない | S&P 500、先頭1000件、空結果に置換して全米株取得成功とする |

[Issue #58](https://github.com/TakamKaji/tradingview_mcp_support/issues/58)の過去生成物`screen_prime_sma25.py`と`run-prime-sma25.bat`は、上記の母集団代替・失敗スキップ・旧BATパスの不合格例です。**元スクリプトの実際の実行失敗原因はログ未提出で未確定**です。文書上の不整合から全原因を断定せず、この個別スクリプトの修理・製品追加は行いません。この表はAIの期待判断であり、Provider実取得や各AIの遵守を実証するものではありません。

## 利用者が送る依頼文

> https://github.com/TakamKaji/tradingview_mcp_support の `docs/user/AI_JSON_GUIDE.md` とリンク先の実仕様・Schema・サンプルを確認してください。私の希望から、単一Screening JSONで可能なら必ずJSON方式を選び、Jobは必要な場合だけ作成してください。表現できない複合処理だけPythonを選び、理由と必要なデータ・環境を説明してください。未確認の条件やAPIは創作せず、取得制限を明示してください。完成ファイル、保存先、検証・実行手順を教えてください。今回はファイル作成とローカル検証までとし、TradingViewへの実取得・書き込みとScheduler登録は行わないでください。

Pythonを必要とする依頼例：

> ランキング確定後に別時間足で判定したいです。まず単一JSONで可能か確認し、不可なら理由を説明して複合Python処理を作成してください。既存の公式MCPクライアントと安全機構を再利用し、母集団・指標の出所・時点と段階ごとの件数を記録してください。未取得・欠損を0件成功として扱わず、実取得やWatchlist同期はまだ行わないでください。

## 方式A：JSONの作成ルール

- **正しいJSONだけをファイルへ保存。** UTF-8（BOMなし）、コメント・余計な末尾カンマ・Markdownコードフェンスなし。JSON全文を省略しない。
- 新しいファイル名は英数字で始め、続きは英数字・`_`・`-`のみ。パス・空白・日本語・Windows予約名は使用禁止。`screenings/<name>.json`や`jobs/<name>.json`の`<name>`をJSON内の`name`と一致させ、既存サンプルを上書きしない。
- Screeningの`schemaVersion`は整数`1`、`limit`は整数1～1000、`columns`は空でない配列。通常の数値`filters`は`[下限, 上限]`で、片側の制限なしは`null`。例：`"pe":[0,15]`、`"div_yield":[3,null]`。フィルター名と取得列名は異なる場合がある。
- **Providerの未確認フィルター・列・市場・presetを創作しない。** 未対応・不明な希望は利用者に伝え、勝手に別条件や別Universeへ置き換えない。`mcp tools`はツール一覧表示であり、任意Toolの実行用CLIではない。
- ScreeningのWatchlistは最初`{"enabled":false}`。Jobは`schemaVersion=1`、`task.type="screening"`、`task.definition`に**Screening名**、`enabled=false`、`output.save=true`、`output.watchlistSync=false`。Jobの`schedule`は手動実行でも必須。現行Schedulerは`daily`、`HH:MM`、`Asia/Tokyo`のみに対応。時刻の希望がなければ例示時刻を明示し、実際の定期登録をしない。
- **Watchlistへの銘柄追加・削除やTask登録・削除はユーザーの明示依頼なしに行わない。** 同梱`sample_screen_daily`は`enabled=true`かつWriteあり。`schedule apply`は有効な**全Job**を登録・更新するため、自動実行しない。
- 全米株の条件なし全件取得はProvider制約で未対応。OHLCV・ニュース・財務を直接取得する専用CLI・定期取得Jobも未実装。Schemaに合うこととTradingViewで取得成功することは別。未実行の実機検証を成功扱いしない。

## 方式A：成果物と確認

1. 完全な`screenings/<name>.json`と、希望された場合は`jobs/<name>.json`を用意する。
2. 希望した条件とJSONフィールドの対応、未対応・未確認事項を短く説明する。
3. CodexはJSON構文・Schema・ファイル名・Job参照先をローカルで検証する。[load_screening_by_name](../../src/tradingview_screening/screening/validators.py)と[load_job_by_name・validate_job_screening_reference](../../src/tradingview_screening/jobs/loader.py)はMCPへ接続せず検証できる。Screeningの読込後は内部の`name`と指定ファイル名の一致も照合する。専用のvalidate CLIはない。利用可能なプロジェクト環境で検証し、未実行なら理由を報告する。
4. **利用者が実取得を依頼した後**はWindowsのコマンドプロンプトで`app.bat screen <screening_name>`、結果は`app.bat results latest <screening_name>`。`screen`はTradingView Readとローカル保存だけでWatchlistを更新しない。Jobなら`app.bat run <job_name>`。`enabled=false`でも手動runは実行する。結果参照は**Job名でなくScreening名**。失敗後の`latest`は古い成功結果の場合があるため日時も確認する。PowerShellは`.\app.bat`、Dockerは[Docker導入](DOCKER.md)を参照。
5. 修正依頼時は指定された条件だけを変え、既存ファイルを意図せず変更しない。

## 方式B：Pythonの再利用箇所と境界

**汎用pipelineエンジンや複合処理専用CLIは未実装です。** 自作Pythonは標準`screen`やJobの`task.definition`にファイル名・Tool名を指定しても実行できません。既存のbuiltinは任意Pythonを起動する仕組みではありません。

| 役割 | 再利用する既存実装・条件 |
| --- | --- |
| 公式MCP接続・型付き呼び出し | [TradingViewClient](../../src/tradingview_screening/integrations/tradingview/client.py)と[Request Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。既存の認証・接続経路を使う |
| OAuth・通信制御 | [auth.py](../../src/tradingview_screening/integrations/tradingview/auth.py)と[RequestGovernor](../../src/tradingview_screening/common/request_governor.py)。既存の資格情報管理、Rate Limit・Retry・Timeout・Concurrency・Cacheを通す |
| Screeningの取得・正規化 | [engine.py](../../src/tradingview_screening/screening/engine.py)と[正規化](../../src/tradingview_screening/integrations/tradingview/screener_normalization.py)。再利用できる単一取得段階に使用する |
| 結果保存 | [results.py](../../src/tradingview_screening/screening/results.py)。既存Screening結果契約に適合する場合だけ利用。任意Tool応答や外部データの自動保存・履歴比較はない |
| 管理Watchlist同期 | [watchlist_sync.py](../../src/tradingview_screening/screening/watchlist_sync.py)と[managed_watchlists.py](../../src/tradingview_screening/screening/managed_watchlists.py)。管理対象識別・差分・ロック・書込後確認を維持する |

独自HTTP認証・token保存、非公式TradingView API、TradingViewのスクレイピング・無断のブラウザ操作を追加しない。別MCPサーバー（`tvmcp`等）の導入を必須にしない。

Pythonラッパーの存在は、Providerで希望データを取得できる保証ではありません。`get_ohlcv`はOHLCV取得であり、公式RSI計算機能とは案内しません。`get_technicals_rating`の時間足指定も、希望するRSI14値が返る保証ではありません。列・時間足・期間を実資料で確認し、不明なら取得可能と断言しないでください。**配布用コアにOHLCVからRSI等を再計算する機能を先回り実装しません。**

### データと失敗を追跡する

- 上記方式選択フローで利用が認められた外部の構成銘柄等は、出典URL（提供ファイルならファイル名と出典）、取得時刻（タイムゾーン付き）、対象日、母集団件数、欠落・重複、利用条件・ライセンス、取得制限と失敗時の挙動を示す。銘柄コードとTradingView symbolの対応・未照合件数も記録する。評価済・未評価件数と完全性を検証し、承認があっても全件確認を省略しない。
- 段階ごとの入力・取得・除外・残存件数と欠損理由、ランキング基準・対象日・同順位の扱いを記録する。母集団の確認とランキング全体の網羅性は別に検証する。`totalCount`と`returnedCount`、上位N件と全件を区別する。最大1000行・未確認のページングを全件取得手段として案内しない。
- 日足出来高の対象日、RSIの出所・時間足・期間・更新時点、確定足/形成中の足を明示する。異なる日時の値を暗黙に同一視しない。時間足不明・欠損・部分取得なら「完全な上位100件」「全市場の該当銘柄」と報告しない。
- 保存する段階別結果、実行時刻、エラー、完全性の根拠、最終結果形式を決める。複合処理・外部データを単一Screeningのfingerprintや`source=tradingview_official_mcp`だけで表したことにしない。既存契約に合わなければ拡張側の別形式・保存先を示し、標準`results`で読めると偽らない。
- 取得失敗や部分成功を正常0件へ変換しない。**全段階の必要データと結果の妥当性を確認できない場合はWatchlist同期を中止する。** 既存の同期関数だけで複合処理全体の完全性が検証されるとは扱わない。

### 使える成果物として提供する

利用者のローカル拡張と製品本体へ一般化して取り込む変更を区別します。条件ごとの使い捨てPythonを本体`src/`へ増やさず、利用者と決めた拡張用フォルダに保存します。**実際に作成したファイルのパス、必要モジュール・依存、Python環境、作業ディレクトリと起動コマンド、検証方法、結果の保存先・読み方**を示してください。Windows Embedded PythonまたはDocker環境への組み込み可否も確認し、未検証の起動手順を動作済みとしないでください。

## ChatGPT・Codexの成果物と操作の境界

- **ChatGPT通常チャット**：完成JSONまたはPython・必要設定をダウンロード可能なファイルで渡す。生成機能が使えなければ完全な本文を提供し、保存先・保存手順を説明する。利用者PCへ自動設置・実行したとは説明しない。Pythonの編集・検証が必要ならCodex等のローカル環境へ引き継ぐ。
- **Codex**：アクセス可能なローカルのアプリフォルダへ保存・検証する。方式Aは構文・Schema・参照先、方式Bは構文・依存・処理順・欠損/失敗時の同期中止をローカルで確認する。必要な実行環境がなければ未検証範囲を示す。通常の条件作成にGitHubへのpush・PRは不要。
- **両方式共通**：選んだ方式と理由、作成ファイル、希望と設定の対応、未対応・未確認事項、検証済み範囲を短く報告する。未実行の実取得・テスト・Writeを成功扱いしない。修正時は指定された条件だけを変える。

**WriteとSchedulerは明示依頼がある場合だけ。** [Watchlist同期](WATCHLIST_SYNC.md)は銘柄の追加・削除を伴い、正常0件なら管理Watchlistを空にします。対象・差分と副作用を説明し、異常結果を空リストとして同期しないでください。Write失敗を自動再送・rollbackせず、token・認可code・credential・Provider生応答全文をチャットへ貼らないでください。

同梱`sample_screen_daily`は`enabled=true`かつ`watchlistSync=true`。`schedule apply`は**有効な全Job**を登録・更新するため、自分のJobだけでなく全定義を点検してください。定義を作っただけでは登録しません。[既存のProvider・CLI制約](FEATURES.md)は両方式で守ります。

## English note

Read the actual manuals, schemas, Provider-supported fields and bundled examples before choosing an implementation. Japanese documentation is authoritative. If files are inaccessible, ask for attachments or their contents; do not claim to have read them.

- **A — standard JSON, always preferred when sufficient:** Create `screenings/<name>.json`; add `jobs/<name>.json` only when requested. Supported market/filter/sort/limit/columns/symbolset/preset combinations do not need custom Python or BAT files. Japanese stocks with PER/yield filters, volume descending and limit 20 belong here. Clarify PER bounds and forecast versus TTM yield; the bundled `div_yield` filter uses forecast yield.
- **B — custom Python, only when a single Screening cannot express the request:** Fixing the Growth-market top 100 by daily volume, then filtering those symbols by 1-hour RSI14 <= 40 requires ordered stages. Filtering RSI before ranking changes the meaning. Explain why Python is needed and verify universe coverage, ranking completeness, indicator source/timeframe/period and timestamps before claiming feasibility.
- Prefer standard JSON and `app.bat screen <name>` for retrieval; limit Python to necessary post-processing when JSON can obtain the data. Otherwise reuse the existing official TradingView MCP client, OAuth, request governor, normalization, compatible result storage and managed Watchlist safeguards where applicable. No generic pipeline engine or custom-Python CLI/job runner is implemented. Wrappers do not guarantee Provider data availability. Do not invent filters, columns or APIs, require another MCP server, or add core RSI calculations in advance.
- If the requested conditions or universe cannot be verified, stop and report BLOCKED or PARTIAL with reasons. Do not silently substitute a universe. When universe completeness is blocked, include relevant alternatives with documented full-retrieval history in the initial report, following the rules above; do not invent candidates, guarantee current retrieval from past success, or execute an alternative before explicit user selection. Recheck official MCP capabilities when they become available; Prime is not permanently unsupported.
- Offer external sources such as JPX as alternatives, but do not fetch, introduce or build an external universe until the user explicitly selects or approves that method. A request to screen with this tool alone is not approval. User-provided files may be used within the user's instructions. Official MCP documentation research is distinct from adopting external screening inputs. For approved external data, report source, retrieval time, reference date, universe count, symbol mapping, missing/duplicate/unmatched symbols, evaluated/unevaluated counts, completeness, limits and usage terms. Never convert failure into a successful empty Watchlist sync. Custom results need an explicit format and storage path; standard result history does not automatically support them.
- ChatGPT provides complete files and save instructions; ordinary chat cannot install them on the user's PC. Codex saves and validates in an accessible local environment. For Python, provide actual paths, dependencies, interpreter, working directory, launch command and result-reading instructions. Report unverified steps honestly.
- File creation, offline validation, live reads and writes are separate actions. Keep Watchlist writes and scheduling disabled initially; never write to TradingView or register/remove scheduled tasks without explicit user instructions. Sync adds/removes symbols, and a valid empty result clears the managed Watchlist. The bundled `sample_screen_daily` enables writes; `schedule apply` affects **all enabled jobs**.

[AI CLI操作](AI_USAGE.md) / [利用者マニュアル](README.md)
