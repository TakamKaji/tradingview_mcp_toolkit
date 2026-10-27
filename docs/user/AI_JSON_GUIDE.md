# AIによるScreening生成ガイド：標準JSONと高度なPython処理

この文書は**Gemini CLI・Codex・Claude Code・ChatGPT共通の作成・実行ガイド**です。**単一Screeningで表現できれば方式A（JSON）を必ず優先し、表現できない処理だけ方式B（Python）を選びます。** 日本語を正本とし、末尾に英語の要点を載せています。標準利用ではCodex・Git・ホストへのPython導入は必須ではありません。高度なPython処理には、ソースを編集・検証できる実行環境が必要です。

本リポジトリは、TradingView公式MCPを既存のPythonラッパーとCLIから利用するためのものです。**利用者に公式MCPサーバーをAIへ別途登録・設定させず、実装済みの`TradingViewClient`と型付きRequestを通じてRead機能を使います。** 標準CLIの公開範囲とPythonラッパーの提供範囲を分けて判断してください。

## AIが確認するファイル（この順）

1. [README](../../README.md)、次に[このガイド](AI_JSON_GUIDE.md)、[機能の対応範囲](FEATURES.md)
2. [Screeningの全項目・条件・制約](SCREENING_MANUAL.md)、[条件カタログと検証状態](SCREENER_CONDITIONS.md)、必要なToolの[公式MCP機能マニュアル](OFFICIAL_MCP_MANUAL.md)
3. Jobが必要なら[Jobの全項目・時刻・副作用](SCHEDULE_MANUAL.md)
4. 実際のサンプル：[Screening](../../screenings/public_japan_value.json)・[読み取り専用Job](../../jobs/public_sample_screen_daily.json)
5. 実際の[Screening Schema](../../src/tradingview_screening/screening/schema.py)・[Job Schema](../../src/tradingview_screening/jobs/schema.py)、[公式Providerの資料](https://www.tradingview.com/mcp/docs)・[型付きRequest](../../src/tradingview_screening/integrations/tradingview/schemas.py)

**必ず実際のファイルを読んでから作成してください。** 公開URLでもAIの閲覧機能やアクセス権によっては本文を読めません。読めないAIは閲覧したふりをせず、上記資料の添付・本文の提供を求めてください。Privateの間は通常の公開URLでは閲覧できません。新しいfilter・列・市場等はProviderの対応を確認し、Schemaが文字列を受理するだけで対応済みとしないでください。

## AIによる方式選択フロー

先に市場・元の母集団・条件・処理順・取得範囲・ランキング件数・時間足/指標期間・基準日時・保存・Jobの要否を固定します。そのうえで、**公式MCPのScreener/Discovery → 既存の型付きReadの組合せ → 必要時の公式OHLCVからのローカル計算 → 制約の報告・選択肢の提示**の順に調査します。外部データ取得は標準フォールバックに含めません。

### Step 1：標準Screeningで直接実現できるか

- 上記README・本ガイド・FEATURES・SCREENING_MANUAL、実Schemaとサンプルを読み、`run_screener`の市場・母集団・条件・指標・並び順で依頼を表せるか調べる。
- [条件カタログ](SCREENER_CONDITIONS.md)の基準日・検証範囲と[最新の公式Provider資料](https://www.tradingview.com/mcp/docs)を確認し、必要なら既存`TradingViewClient.get_screener_columns()`等の少量Readで列・時間足・期間を調査する。**列の取得対応と同名のfilter対応は別**。Discoveryや列検索で見つからないだけで不存在と断定せず、未確認と非対応を根拠付きで分ける。Schemaが文字列を受理するだけでも対応済みとせず、未知のfilter・引数・市場指定を作らない。
- 指標の対象市場・期間・価格基準・日時、条件の適用順を確認する。返却の`ignored_filters`等、実際の条件適用、`totalCount`と取得件数・完全性を確認し、条件の無視や切捨てを成功にしない。無視の申告がないだけでも適用を保証しない。
- 単一JSONで正しく実現できるなら**方式Aを最優先**し、`screenings/*.json`を作る。Jobは依頼された場合だけ作り、通常条件ごとのPython/BATは増やさない。

### Step 2：既存ラッパーのReadを組み合わせられるか

JSONでは表せない場合、実装済み`TradingViewClient`と型付きRequestの`run_screener`、`get_screener_columns`、`get_symbol_data`、`get_symbol_data_batch`、`get_technicals_rating`、`get_ohlcv`、`search_symbols`を調べます。Screenerの候補抽出→既存指標の直接取得・一括取得→必要ならOHLCVからのローカル計算、という処理で**方式BのPythonを作成**します。2026-10-27の別環境での公式MCP直接実行では、列DiscoveryのSMA検索が不一致でも`SMA25`をScreener取得列・単体・一括Readで利用できました（[条件カタログ](SCREENER_CONDITIONS.md)）。**この観測は本ラッパーでの再現成功を意味しません**が、Discovery不一致のみで直接取得経路を打ち切らないでください。後続の直接実験では`SMA13`/`EMA25`/`RSI7`、`RSI|60`/`EMA25|1W`等も数値取得できました。一方、`EMA25`/`SMA13`はfilterで`ignored_filters`に入りました。第2ラウンドでは`RSI24/48/96/192`、`SMA48/96/192`、`EMA48/96/192`は日米代表銘柄でnullになり、**任意整数期間の一般対応は確認されていません**。既定`RSI`が14期間Wilder計算とほぼ一致しても、`RSI14`という列名はnullでした。対して`RSI7`、標準`MACD.macd`/`MACD.signal`は日経225のScreenerでfilter適用に成功し、時間足付きRSIのfilterは無視されました。希望する期間・時間足の列を少数銘柄で試し、成功した列だけ直接利用し、別途filter対応を確認します。専用CLIや直接指標がないという理由だけで実装不能としません。

候補抽出を使うなら、本来の該当銘柄がすべて候補集合に含まれる根拠を確認します。必要条件による絞込みか、取得上限で切れていないか、元の市場/母集団と処理順を保つかを検証してください。出来高上位100件を全プライムの代理にする等、取りこぼす候補取得を無断で採用しません。網羅性を確認できない候補は評価範囲を限定して報告し、完全な抽出とはしません。

### Step 3：制約を報告し、変更・外部データ利用は承諾を得る

公式MCPだけで元の母集団・条件を成立させられない場合は、調べたRead/引数・確認済み制限・未検証事項と不足データを説明します。未確認なら必要な少量Readによる調査を続け、調査できない理由も示します。JPX・Yahoo Finance等への自動フォールバックや、代表銘柄への置換で成功にしません。

**条件・母集団の変更と、外部データの取得・利用は、ユーザーの明示的な依頼・承諾がある場合だけです。** 「このツールで作成・実行」は外部データ利用の承諾を含まず、JPXのように外部データの出典が公式でも、承諾なしに取得しません。必要なら変更点を示した選択肢として提案し、承諾前は実行しません。承諾済みの外部利用は別の拡張処理とし、公式MCPの取得経路・結果の出所と分離してproductionへ混入させません。出典・基準日・期中異動・シンボル対応・完全性等は下記の追跡契約に従います。

**作成と完全取得の成功保証は別です。** 事前の全件保証や接続確認が揃わなくても、実用可能ならスクリプトを作成し、実行時に評価済/未評価/失敗件数・完全性を検証します。必要データや接続が使えない時は具体的な不足条件と未実行/失敗状態を示し、架空データや別母集団で成功にしません。作成だけの依頼で実取得せず、実行も依頼され環境が利用可能なら実行・検証します。明示依頼のないWriteやScheduler登録・削除は行いません。

| 希望 | 選択 | 成果物・理由 |
| --- | --- | --- |
| 対応済みの市場・filter・sort・limit・columns、任意のsymbolset・preset | **A：標準JSON** | 単一Screeningで表現可能。Screening JSON、必要な場合だけJob JSON |
| 複数段階の抽出、ランキング確定後の別時間足判定、承諾済み外部母集団との照合 | **B：複合Python** | 単一JSONには段階・結合・後段判定を記述できない。Pythonと必要設定・依存・起動手順 |
| 直接のProvider指標や全件保証を事前確認できないが、既存Readラッパーとデータ処理で実用可能 | **B：作成し、制約を明記** | 直接指標・一括取得を先に調べ、必要ならOHLCV計算。外部母集団はStep 3の条件時だけ使う。作成を完全取得の成功とは扱わない |
| 必要データ・接続が利用できない | **制約と実行状態を報告** | 作成可能な成果物と不足条件を示す。実行不能なら未実行、実行失敗なら失敗とし、架空データや別母集団で成功にしない |

### 条件提示・代替案の契約

元の市場・母集団・条件・閾値・時間足・指標期間・処理順を保持します。直接対応が未確認なのか、試した指定が非対応だったのかを[カタログの状態区分](SCREENER_CONDITIONS.md#状態と今回の確認範囲)で示し、方式Bの既存Read・Python処理で元の要求を実現できるか先に調べます。実用可能な方式Bを、直接filterがないという理由で打ち切りません。

条件の変更が必要なら、Providerで確認できた代替案や外部データ利用案を**最大3件程度**に絞り、各案で元の要求から変わる市場/母集団・条件・閾値・時間足・期間・取得元と、検証状態・制約を説明します。元の条件を方式Bで保てる場合は、その方法も選択肢に含めます。**利用者の承諾なしに変更案や外部データ利用を採用・実行しません。** 元の条件を保つ公式MCPによる方式Bの作成・依頼済み実行には、追加の承諾待ちを設けません。

簡単な依頼で長い条件一覧を毎回表示せず、条件を尋ねられた時や要求の変更が必要な時だけ、該当項目を簡潔に提示します。

### 判定例（条件固有のファイルは同梱しない）

**ケースA：「日本株でPER15倍以下、配当利回り3%以上を出来高順で20件取得する」→ 方式A。** `market=japan`、`pe`・`div_yield`、`sortBy=volume`、`sortOrder=desc`、`limit=20`で表現できる。同梱例の`pe=[0,15]`は負のPERを除外し、`div_yield=[3,null]`は**予想配当利回り**を使う。PERの上限だけなら`[null,15]`との違いを説明し、利回りの基準も確認する。TTMを求められた場合、未確認のfilterへ置き換えない。Jobの希望がなければScreening JSONだけを提供する。

**ケースB：「グロース市場全体を対象に日足出来高上位100件を確定してから、1時間足RSI14が40以下の銘柄を抽出する」→ 方式B。** 「母集団を確認 → 日足出来高で順位確定 → その100件だけに1時間足RSI14の判定 → 保存」という順序が必要。現行の単一Screening JSONには段階や独立した時間足の後段判定を表す項目がない。Job JSONも単一のScreening参照でこの順序を追加できない。

最初からRSI条件を併用して取得すると、**RSI条件を満たす集合の出来高上位100件**になり、依頼と異なる。日本株の先頭1000件を取ってからグロース市場と照合しても、市場全体の上位100件とは保証できない。まず既存ラッパーで母集団・日足出来高→順位確定→1h RSI14直接取得を調べ、必要ならOHLCV計算へ進む。母集団を確定できなければ制約を説明し、外部一覧は明示的な依頼・承諾後だけ使う。未取得があれば順位や判定の完全性を明示し、評価済範囲と元の母集団全体を区別する。この2例は方式選択の説明であり、実取得の成功を示すものではない。

## 母集団・完全性・テクニカル指標の検証契約

「市場」「取引所」「上場区分」「全件」「ランキング」と「フィルタ適用順」を別々に固定します。`market=japan`は東証プライムの指定ではありません。**プライム全体→主要63銘柄、全米株→S&P 500、市場全体→先頭1000件、指定指標期間→別期間を無断で変更しません。** 小規模Readのテスト結果は調査・部分確認であり、元の全件依頼の完了とは区別します。Provider対応は[公式資料](https://www.tradingview.com/mcp/docs)、型付きRequest、必要なら既存Clientの`get_screener_columns`によるReadで確認します。列の存在だけでは、その市場でのフィルタ対応や期間・時間足まで保証しません。

- 対象母集団件数、評価済件数、未評価件数、失敗件数、完全性、対象時点を報告する。総件数不明は「不明」とし、未評価0とはしない。失敗件数は未評価のうち取得・計算等が失敗した件数として示し、二重加算しない。「母集団全体で該当0件」は必要な全対象を正常に評価できた場合にだけ結論とする。不完全な実行でも「評価済範囲では該当0件」と範囲を限定して報告できる。
- 標準結果の`totalCount`は**その問合せ条件**の総件数、`returnedCount`は取得行数。`completeCoverage=true`でも別途確認していない上場母集団の完全性は示さない。現行Engineは`status=success`でも`completeCoverage=false`を返し得るため、成功ステータスだけで全件取得と説明しない。標準JSONにない評価件数等は検証報告で補い、結果Schemaを勝手に追加・変更しない。
- `RunScreenerRequest`は最大1000行で、全件列挙用のoffset/page引数はない。`get_news`のページングをScreenerへ転用しない。10/27の**公式MCP直接実行**では、確認済みの`close`数値filterで価格帯を分け、各区間を上限内に収めて取得できました。元の母集団・区分を変えずに分割できる場合は、境界・重複・各区間の`totalCount`/行数・filter適用を照合する方法も検討できます。ただし分割取得は全市場・元母集団の完全性を自動的に証明せず、ラッパー経由での実行も別途検証が必要です。全件を保証できない時は制約を明示し、母集団・条件を緩和せず完全取得の成功報告を止める。
- 25日SMAは、同じ基準日の**確定日足の終値25本**で計算可能か確認する。OHLCVを使う場合は`interval="1D"`で、生の足が必要なため`summary=false`とし、進行中足の除外後にも25本確保する。日時を解釈して昇順に整え、重複、非数値・欠損、取引日の抜け、株式分割等の価格調整の整合を検証する。休日を欠損扱いせず、25暦日や直近25行というだけで25取引日とみなさない。25本未満・日付不明・未確定足混在を無言でスキップしない。
- 基準価格を同じ確定日の終値`C(t)`とするなら、`SMA25(t)=直近25確定日足終値の平均`、`乖離率=(C(t)/SMA25(t)-1)*100`と示す。SMAが0・欠損なら評価不能。未指定の「20%以上」は通常**+20%以上**と解釈して報告し、絶対値20%以上（下方乖離を含む）へ変えない。進行中の現在値を使う依頼ならSMAとの時点差と計算基準を明示する。
- 同じ期間・時間足・価格基準の正しいProvider指標を直接取得できれば再計算を避ける。例として`RSI7`は直接Read/filter対応を確認しましたが、`RSI48/96/192`、`SMA48/96/192`、`EMA48/96/192`は10/27の直接MCP試験ではnullでした。希望期間が値を返さない場合は、既存`get_ohlcv`の足を検証して**方式Bのローカル拡張Pythonで計算できる**。必要本数・計算方式・初期値・時点を定義し、入力不足は評価不能として記録する。今回の日足RSI7/SMA13/EMA13はローカル計算と一致しましたが、1h/4hでは一部差が残りました。`interval`/指標suffix、バー開始時刻・セッション・確定状態・同一価格系列を確認し、一致しない場合は検証未完として扱います。Publicコアに新しい指標計算を追加しないという製品開発ルールを、依頼されたローカルPythonでの計算禁止と取り違えない。

## Windowsの起動契約

正式な利用者入口は[setup.bat](../../setup.bat)、[app.bat](../../app.bat)、[export-results.bat](../../export-results.bat)。内部BATは[scripts/setenv.bat](../../scripts/setenv.bat)と[scripts/setup-runtime.bat](../../scripts/setup-runtime.bat)です。旧ルート直下の`setenv.bat`を呼ぶ生成物は不合格です。条件ごとの新規BATを安易に作らず、通常は既存`app.bat`を使います。

複合Pythonに実行環境の設定が必要な場合だけ、プロジェクトルートのコマンドプロンプトで`call scripts\setenv.bat`後、`"%PYTHON_EXECUTABLE%" <拡張スクリプトのパス>`を使います。BAT内の相対パスはBATの保存場所から解決するため、場所を確認せず`%~dp0setenv.bat`を生成しません。PowerShellからBATを単独実行しても親PowerShellへ環境変数は引き継がれません。同じcmdプロセスで設定とPython実行を行ってください。

Embedded PythonとホストPythonの`site-packages`を`sys.path`で混在させない。`PYTHONHOME`/`PYTHONPATH`のクリアは既存起動プロセス内に限定し、OSのPATH・レジストリを恒久変更しない。`USERPROFILE`・`HOME`・`APPDATA`等をプロジェクト配下へ置換せず、OAuth・Credential Managerは通常のWindowsユーザー環境を保ちます。

## 「作成して実行」の完了契約

1. 方式・データ取得可否・実行環境・接続・Read権限を確認する。「作成して実行」の依頼に対し、環境と権限が利用可能なら既存MCPのRead取得・計算・ローカル保存・結果検証まで行う。エージェントによる実行を一律禁止と解釈しない。できなければ実行環境・権限・認証・必要データのどこが使えないかと実際の根拠を示し、認証情報削除で解決しようとしない。
2. 実行前の時刻と既存最新結果を控える。方式AはRead-onlyの`app.bat screen <name>`等、方式Bは作成したPythonを既存Embedded Python等で起動する。Jobの場合は実際の参照定義と`watchlistSync`等を確認し、暗黙のWriteがあれば実行しない。
3. 実際のstdout、stderr、exit codeを確認する。exit 0だけで完了とせず、`status`・`errors`・coverageを調べる。診断ログの秘密値は報告しない。
4. 新しい保存ファイルの実在、内容、今回の実行との対応を照合する。標準結果は`executedAt`、Screening名、条件のfingerprintを確認し、方式Bの別形式なら定義した実行日時・母集団・条件・評価/失敗件数を確認する。`results latest`は過去の成功結果を返し得るため、古いファイルを今回の成功証跡にしない。実行失敗と過去結果は分けて報告する。
5. **成功・部分成功・失敗・未実行**を区別する。全件依頼で網羅性を証明できない場合は完全成功にしない。独自Pythonの結果は標準Screening形式・履歴比較への適合を確認できる場合だけ互換と説明する。

報告項目：方式（JSON/Python）と理由、実行コマンド・作業場所、元の母集団範囲、対象/評価済/未評価/失敗件数、coverage、閾値・方向、基準日時と実行日時、exit code・エラー、今回の保存先、状態。実行不能なら再現コマンドと実際に確認できたエラーまたは不足条件を示す。ファイル保存やSchema検証だけを実行成功としません。

Watchlist更新、Alert Write、Scheduler登録・削除、認証情報削除には**個別の明示依頼**が必要です。「スクリーニングして実行」だけでは許可されません。結果JSONが正本で、HTML/CSVは必要時に既存exportを使います。

## 自然言語の回帰ケースと不合格例

まず「このフォルダの使い方を理解して」、次に「このツールを使って東証プライムに上場している企業の中から25日移動平均線との乖離率が20％以上の銘柄をスクリーニングするスクリプトを作成し実行してください。」と依頼された場合も、README→本ガイド→実Schema・サンプル・BATを確認し、次の判断を行います。利用可能なら正しい方式で実行証跡まで検証し、不可なら不足する母集団・指標・接続の根拠を示して未実行/失敗と報告します。「スクリプト」という語だけでPython/BATを選びません。

| 入力ケース | 期待判断 | 不合格例 |
| --- | --- | --- |
| 東証プライム全体、SMA25乖離率+20%以上 | 公式Screener/Discovery→既存Read→必要時の公式OHLCV計算を調べる。未確認なら断定せず調査し、元の母集団・条件が成立しなければ根拠と制約を報告。外部利用や条件変更は提案し承諾後だけ実行 | 未確認を非対応と断定、JPX自動取得、主要63銘柄・日本株全体へ無断変更、小規模確認を全件完了とする |
| 日本株PER15倍以下、予想配当利回り3%以上 | 確認済みpe/div_yieldを使う標準JSONを優先。PERの下限・予想配当の基準を上記判定例に従い確認 | 不要なPython/BAT・外部データ、TTMへの無断変更 |
| 指定3銘柄のSMA25計算 | 指定母集団を保持し、必要なら既存MCPのOHLCVを使うPython。上記の時系列・確定足・欠損・価格調整の契約を検証し、実行依頼と環境/権限があれば実行・結果検証 | 外部銘柄一覧の追加、別銘柄への置換、未検証の直近25行で成功扱い |
| JPX公式一覧の利用を明示的に許可 | 承諾範囲で外部データを別の拡張処理として取得・利用可能。公式MCP経路と分離し、出典・基準日・対応付け・母集団完全性を検証 | 外部取得をproductionへ追加、承諾範囲外の取得先や母集団変更、外部データを公式MCP由来とする |

[Issue #58](https://github.com/TakamKaji/tradingview_mcp_support/issues/58)の過去生成物`screen_prime_sma25.py`と`run-prime-sma25.bat`は、上記の母集団代替・失敗スキップ・旧BATパスの不合格例です。**元スクリプトの実際の実行失敗原因はログ未提出で未確定**です。文書上の不整合から全原因を断定せず、この個別スクリプトの修理・製品追加は行いません。この表はAIの期待判断であり、Provider実取得や各AIの遵守を実証するものではありません。

## 利用者が送る依頼文

以下は**作成・ローカル検証だけを依頼するサンプル**です。「実取得しない」はこのサンプルの依頼範囲に限り、全作業共通の禁止ではありません。実際に「作成して実行」と依頼された場合は上記の[完了契約](#作成して実行の完了契約)を適用します。

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
- 標準Screenerでの全米株の条件なし全件取得はProvider制約で未対応。OHLCV・ニュース・財務を直接取得する専用CLI・定期取得Jobも未実装だが、既存Pythonラッパーからの取得とは区別する。Schemaに合うこととTradingViewで取得成功することは別。未実行の実機検証を成功扱いしない。

## 方式A：成果物と確認

1. 完全な`screenings/<name>.json`と、希望された場合は`jobs/<name>.json`を用意する。
2. 希望した条件とJSONフィールドの対応、未対応・未確認事項を短く説明する。
3. CodexはJSON構文・Schema・ファイル名・Job参照先をローカルで検証する。[load_screening_by_name](../../src/tradingview_screening/screening/validators.py)と[load_job_by_name・validate_job_screening_reference](../../src/tradingview_screening/jobs/loader.py)はMCPへ接続せず検証できる。Screeningの読込後は内部の`name`と指定ファイル名の一致も照合する。専用のvalidate CLIはない。利用可能なプロジェクト環境で検証し、未実行なら理由を報告する。
4. **利用者が実取得を依頼した後**はWindowsのコマンドプロンプトで`app.bat screen <screening_name>`、結果は`app.bat results latest <screening_name>`。`screen`はTradingView Readとローカル保存だけでWatchlistを更新しない。Jobなら`app.bat run <job_name>`。`enabled=false`でも手動runは実行する。結果参照は**Job名でなくScreening名**。失敗後の`latest`は古い成功結果の場合があるため日時も確認する。PowerShellは`.\app.bat`、Dockerは[Docker導入](DOCKER.md)を参照。
5. 修正依頼時は指定された条件だけを変え、既存ファイルを意図せず変更しない。

## 方式B：Pythonの再利用箇所と境界

**JSONでは表せない処理は、実装済み`TradingViewClient`と型付きRequestを使うPythonを作成します。** 調査順序は上記Step 1〜3に従い、既存指標の直接取得・一括取得を先に検討し、必要な場合に公式OHLCVからのローカル計算へ進みます。外部データ利用の承諾はStep 3を正本とし、母集団が未確定というだけでは許可されません。

汎用pipelineエンジンや複合処理専用CLIは未実装ですが、これは既存ラッパーを呼ぶPythonを作成・直接実行できないという意味ではありません。自作Pythonは標準`screen`やJobの`task.definition`にファイル名・Tool名を指定しても実行できず、既存builtinも任意Pythonの起動機構ではないため、作成したファイルを適切なPython環境から起動します。

| 役割 | 再利用する既存実装・条件 |
| --- | --- |
| 公式MCP接続・型付き呼び出し | [TradingViewClient](../../src/tradingview_screening/integrations/tradingview/client.py)と[Request Schema](../../src/tradingview_screening/integrations/tradingview/schemas.py)。既存の認証・接続経路を使う |
| OAuth・通信制御 | [auth.py](../../src/tradingview_screening/integrations/tradingview/auth.py)と[RequestGovernor](../../src/tradingview_screening/common/request_governor.py)。既存の資格情報管理、Rate Limit・Retry・Timeout・Concurrency・Cacheを通す |
| Read機能の組合せ | `get_screener_columns(GetScreenerColumnsRequest(...))`で列を調査、`get_symbol_data_batch(GetSymbolDataBatchRequest(...))`で最大50銘柄ずつ取得、`get_ohlcv(GetOhlcvRequest(...))`で足を取得。Requestは上記Schemaからimportし、`async with TradingViewClient() as client:`内で型付き関数をawaitする |
| Screeningの取得・正規化 | [engine.py](../../src/tradingview_screening/screening/engine.py)と[正規化](../../src/tradingview_screening/integrations/tradingview/screener_normalization.py)。再利用できる単一取得段階に使用する |
| 結果保存 | [results.py](../../src/tradingview_screening/screening/results.py)。既存Screening結果契約に適合する場合だけ利用。任意Tool応答や外部データの自動保存・履歴比較はない |
| 管理Watchlist同期 | [watchlist_sync.py](../../src/tradingview_screening/screening/watchlist_sync.py)と[managed_watchlists.py](../../src/tradingview_screening/screening/managed_watchlists.py)。管理対象識別・差分・ロック・書込後確認を維持する |

**利用者にTradingView公式MCPサーバーをAI側へ別途登録・設定するよう要求しません。** 必要なのは既存ツールの実行環境とTradingViewの利用権限・既存認証です。独自のMCP通信・OAuth認証・TradingView用HTTPクライアント・token保存を再実装せず、他のMCPライブラリや非公式TradingView APIを勝手に導入しません。TradingViewのスクレイピング・無断のブラウザ操作や別MCPサーバーの導入も行いません。承諾済みの外部母集団は公開配布データや利用者提供ファイルを別拡張として扱い、TradingViewの通信経路は既存Clientに統一します。

Pythonラッパーの存在は、Providerの応答や全件取得の成功を保証しません。そのため、応答・欠損・エラーの検証を実装します。`get_ohlcv`自体は足の取得機能ですが、そのデータを使ったSMA25・乖離率・RSI14等の計算はローカルPythonで行えます。`get_technicals_rating`等で希望どおりの指標を直接取得できるかも調べ、取得できなければOHLCV計算へ進みます。**標準CLIに専用コマンドがない、またはScreenerに指標がないという理由だけで実装を諦めません。** 配布用コア・ラッパー・認証・通信層を変更しないことと、方式Bの利用者用Pythonを作成することを区別します。

### 東証プライムSMA25乖離率の組立手順

1. 既存Screenerでプライム母集団・SMA25・乖離率を直接指定できるか、列/フィルタ・期間・基準日時・対象市場を調べる。単一JSONで正しく表せるなら方式Aを使い、JPX一覧やOHLCVの全銘柄取得を追加しない。
2. 直接表せない時は方式Bとして既存Read関数を調べ、候補取得が真の該当集合を取りこぼさないことを検証し、既存指標の直接取得・一括取得を優先する。母集団を確定できなければStep 3に従い制約を報告し、JPX等の外部一覧は明示的な依頼・承諾があった場合だけ別拡張として利用する。
3. ローカル計算が必要な場合に既存`TradingViewClient.get_ohlcv(GetOhlcvRequest(...))`で`interval="1D"`・`summary=false`の日足を取得する。返却を足配列と決めつけず、実際のResponse契約と応答例で格納場所・日時・値の形式を確認してから解釈する。進行中足を除いた25確定日足、NaN/Inf・欠損・重複・基準日・価格調整を検証する。
4. ローカル計算経路ではPythonで25日SMAと`(基準終値/SMA25-1)*100`を計算して+20%以上を抽出する。非有限値・期間不足・日時不一致は評価不能とする。銘柄単位の回復可能な失敗は理由を残して継続し、共通認証/接続などで中断する場合は途中結果・未評価範囲・中断原因を保存する。NaN比較による偽の条件不適合や、例外の無言スキップを避ける。
5. 元母集団と対象日時、評価済/未評価/失敗件数、銘柄別の欠損理由、取得/実行時刻、該当結果と完全性を保存する。事前の全件保証がなくても実用可能なスクリプトは作成し、部分結果を全プライム成功とは表示しない。
6. 実ファイルの保存先、必要な環境・依存、作業ディレクトリ、正確な実行コマンド、結果の保存先と確認方法を提示する。実行依頼があり環境が使えれば実行し、stdout/stderr/exit codeと新しい結果を検証する。接続や必要データが使えなければ理由を示し、未実行と実行失敗を区別する。

### データと失敗を追跡する

- `ObservedReadResponse`は型付きの応答包絡であり、OHLCV配列そのものではない。`structured_content`の有無、`success`・`error`、Tool別の追加データやpartial/missing等を実際の応答と照合する。OHLCVの足配列・日時・終値等の内部構造は現行Responseモデルだけでは固定されないため、未確認の構造を捏造しない。構造不一致・Provider失敗・数値不正は未取得/失敗として扱い、正常な空データと区別する。
- 公式MCP直接観測ではRead 18 Tool・40呼出しのうち9件はProviderの`success`キーがなく、経済カレンダーは`status:ok`を返しました。ツールごとの応答構造を確認し、`success`キー欠如だけで失敗とは判定しません。逆に`success:true`でも`missing_count`・`ignored_filters`・nullを確認します。PowerShellで`RSI`と`rsi`が共存するJSONを解析する場合、通常の`ConvertFrom-Json`はエラーとなるため`-AsHashtable`を利用できます。これは**公式MCP直接実験での知見**であり、ラッパー全Toolの受入成功ではありません。
- 財務・カレンダー・ニュース・文書をPythonで組み合わせる場合、`period=fy`でもPERがTTMの例、`period=ttm`の裸`net_income`がFY値になる例、`eps` aliasが基本EPSだが財務履歴EPSは希薄化後の例、予想株価の`target_mismatch`などに注意します。10/27の直接MCP試験では、トヨタとソニーのraw予想EPS/売上と`get_forecasts`の値に同一期間ごとに共通倍率の差があり、原因は未確定です。出所・期間・単位・品質フラグが合致しない数値を自動換算・結合しません。日本株の銘柄指定配当0件や指定日付窓外データ、marketモードのrecent/upcomingの配当額の混同、ニュースASTのJSON文字列と文書ASTのオブジェクト差などにも注意します。個別の実機観測・未確認範囲は[公式MCP機能マニュアル](OFFICIAL_MCP_MANUAL.md)を参照します。
- 承諾済みの外部構成銘柄等は、出典URL、取得時刻（タイムゾーン付き）、対象日、母集団件数、欠落・重複、利用条件・ライセンス、取得制限と失敗時の挙動を示す。銘柄コードとTradingView symbolの対応・未照合件数も記録する。
- 段階ごとの入力・取得・除外・残存件数と欠損理由、ランキング基準・対象日・同順位の扱いを記録する。母集団の確認とランキング全体の網羅性は別に検証する。`totalCount`と`returnedCount`、上位N件と全件を区別する。最大1000行・未確認のページングを全件取得手段として案内しない。
- 日足出来高の対象日、RSIの出所・時間足・期間・更新時点、確定足/形成中の足を明示する。異なる日時の値を暗黙に同一視しない。時間足不明・欠損・部分取得なら「完全な上位100件」「全市場の該当銘柄」と報告しない。
- 保存する段階別結果、実行時刻、エラー、完全性の根拠、最終結果形式を決める。複合処理・外部データを単一Screeningのfingerprintや`source=tradingview_official_mcp`だけで表したことにしない。既存契約に合わなければ拡張側の別形式・保存先を示し、標準`results`で読めると偽らない。
- 取得失敗や部分成功を正常0件へ変換しない。**全段階の必要データと結果の妥当性を確認できない場合はWatchlist同期を中止する。** 既存の同期関数だけで複合処理全体の完全性が検証されるとは扱わない。

### 使える成果物として提供する

利用者のローカル拡張と製品本体へ一般化して取り込む変更を区別します。条件ごとの使い捨てPythonを本体`src/`へ増やさず、利用者と決めた拡張用フォルダに保存します。**実際に作成したファイルのパス、必要モジュール・依存、Python環境、作業ディレクトリと起動コマンド、検証方法、結果の保存先・読み方**を示してください。Windows Embedded PythonまたはDocker環境への組み込み可否も確認し、未検証の起動手順を動作済みとしないでください。

起動コマンドは成果物の実名と実際の引数で示し、存在しない専用CLIや新規BATを案内しません。実行も依頼され環境が利用可能なら、ファイル作成や手順提示だけで終えず実行・結果検証まで進めます。実行できない時も、実用可能なPythonを作成できるなら保存し、データ/認証/依存等の不足条件と未実行状態を報告します。

## ChatGPT・Codexの成果物と操作の境界

- **ChatGPT通常チャット**：完成JSONまたはPython・必要設定をダウンロード可能なファイルで渡す。生成機能が使えなければ完全な本文を提供し、保存先・保存手順を説明する。利用者PCへ自動設置・実行したとは説明しない。Pythonの編集・検証が必要ならCodex等のローカル環境へ引き継ぐ。
- **Codex**：アクセス可能なローカルのアプリフォルダへ保存・検証する。方式Aは構文・Schema・参照先、方式Bは構文・依存・処理順・欠損/失敗時の同期中止をローカルで確認する。必要な実行環境がなければ未検証範囲を示す。通常の条件作成にGitHubへのpush・PRは不要。
- **両方式共通**：選んだ方式と理由、作成ファイル、希望と設定の対応、未対応・未確認事項、検証済み範囲を短く報告する。未実行の実取得・テスト・Writeを成功扱いしない。修正時は指定された条件だけを変える。

**WriteとSchedulerは明示依頼がある場合だけ。** [Watchlist同期](WATCHLIST_SYNC.md)は銘柄の追加・削除を伴い、正常0件なら管理Watchlistを空にします。対象・差分と副作用を説明し、異常結果を空リストとして同期しないでください。Write失敗を自動再送・rollbackせず、token・認可code・credential・Provider生応答全文をチャットへ貼らないでください。

同梱`sample_screen_daily`は`enabled=true`かつ`watchlistSync=true`。`schedule apply`は**有効な全Job**を登録・更新するため、自分のJobだけでなく全定義を点検してください。定義を作っただけでは登録しません。[既存のProvider・CLI制約](FEATURES.md)は両方式で守ります。

## English note

Read the actual manuals, schemas, Provider-supported fields and bundled examples before choosing an implementation. Japanese documentation is authoritative. If files are inaccessible, ask for attachments or their contents; do not claim to have read them.

- **A — standard JSON, always preferred when sufficient:** Create `screenings/<name>.json`; add `jobs/<name>.json` only when requested. Supported market/filter/sort/limit/columns/symbolset/preset combinations do not need custom Python or BAT files. Japanese stocks with PER/yield filters, volume descending and limit 20 belong here. Clarify PER bounds and forecast versus TTM yield; the bundled `div_yield` filter uses forecast yield.
- **Discovery order:** Investigate official MCP screening and Discovery, then existing typed Read combinations, then local calculations from official OHLCV when needed. Distinguish unverified support from confirmed limitations; a missing search result does not prove absence. Report constraints if the original universe and conditions cannot be established. External data is never an automatic fallback: require explicit user instructions or consent, keep it in a separate extension, and preserve the official MCP path.
- Consult the dated conditions catalog and current Provider specification. Distinguish unverified support from a rejected key. After investigating the original request through existing wrappers, offer at most about three verified alternatives when needed, explaining every changed constraint. Keep a viable original-condition Python option and obtain consent before adopting or executing a changed request. Do not display the entire catalog for simple requests.
- Use the existing client, authentication and request governor; never require a separate TradingView MCP registration in the AI, reimplement MCP/OAuth/TradingView HTTP transport, or add another MCP library or unofficial API. Local extension calculations from validated OHLCV are allowed; production core changes are outside this workflow.
- For Prime/SMA25, investigate direct screening first, then existing indicator reads and official OHLCV calculations when needed. Never silently replace Prime with 63 stocks, the full US market with S&P 500, the universe with the first 1000 rows, or a requested period with another. Validate the actual response structure, finite values, 25 completed daily bars, dates, duplicates and price adjustments. Create a practical original-condition script when possible, record partial progress and failures, and verify execution when requested and available. Small tests do not complete the original full-universe request.
- For explicitly authorized external data, report source, retrieval time, universe count, missing/unmatched symbols, limits and usage terms. Track counts and errors per stage. Never describe partial retrieval as a complete universe, or convert failure into a successful empty Watchlist sync. Custom results need an explicit format and storage path; standard result history does not automatically support them.
- ChatGPT provides complete files and save instructions; ordinary chat cannot install them on the user's PC. Codex saves and validates in an accessible local environment. For Python, provide actual paths, dependencies, interpreter, working directory, launch command and result-reading instructions. Report unverified steps honestly.
- A request to create and run authorizes official MCP Read, local calculations, saving and result verification when the environment and permissions are available. A sample prompt saying not to fetch data limits only that sample; it is not a general execution ban. If blocked, identify the specific environment, permission, authentication or data constraint. Keep Watchlist writes and scheduling disabled initially; never write to TradingView or register/remove scheduled tasks without explicit user instructions. Sync adds/removes symbols, and a valid empty result clears the managed Watchlist. The bundled `sample_screen_daily` enables writes; `schedule apply` affects **all enabled jobs**.

[AI CLI操作](AI_USAGE.md) / [利用者マニュアル](README.md)
