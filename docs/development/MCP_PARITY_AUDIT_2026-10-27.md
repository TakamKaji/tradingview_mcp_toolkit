# 公式MCP機能同等性監査・検証（2026-10-27）

[Issue #64](https://github.com/TakamKaji/tradingview_mcp_support/issues/64)。調査基準日・実行日は2026-10-27 JST。Toolの存在、引数の受理、データの取得、全件の完全性を分けて記録する。

## 基点・範囲

- 最新origin/develop `0a8cf09a072fe1e1be2264ab02b8c8505db03f71`から`codex/mcp-feature-parity-audit`を作成。
- [PR #63](https://github.com/TakamKaji/tradingview_mcp_support/pull/63)は監査開始時OPEN・未マージ。head `d5d5125dbf8da199fec9ca69ea6557cb1782a679`のマニュアルと検証記録は参照のみ。その変更を取り込まず、同ブランチ/PRを変更しない。
- origin/main `b7ecd7ecabb79b12634739adb353a144b7027295`は変更しない。実装・テスト・レビューはdevelop向けPR1本。配布対象と開発専用変更のコミットを分離する。
- 既存Embedded Python 3.12.8、保存済み認証、型付きRequest、Client、RequestGovernorを使用。Watchlist/Alert Write、active Watchlist、Scheduler、認証設定変更は実行していない。

根拠は[公式公開仕様](https://www.tradingview.com/mcp/docs)、[Client](../../src/tradingview_screening/integrations/tradingview/client.py)、[Request/Response](../../src/tradingview_screening/integrations/tradingview/schemas.py)、[Tool名写像](../../src/tradingview_screening/integrations/tradingview/tool_catalog.py)、[既存API](API.md)、現行テストと当日のDiscovery。公式説明や生応答の全文、個人情報・tokenはcommitしない。

## 結論と差分分類

2026-10-26T23:41:12.544059+00:00（10/27 08:41 JST）のDiscoveryは**35 Tool・109引数**。公式公開ページ35名、既存wire名・ラッパー・Request35個が一致。不足/追加/改名は0。修正前ローカル107引数、共通106引数の型/nullable・必須性に差はない。修正後は110引数となり、109個がDiscoveryと対応し、残り1個は保持したWatchlistのdescription。

| 分類 | 発見・根拠 | 対応 |
| --- | --- | --- |
| A：利用可能な機能がラッパーに不足 | OHLCVのdate_from/date_to/format。live入力Schemaと説明、既存Clientの少量Readで実動作を確認 | 3引数を既存GetOhlcvRequestへ追加 |
| B：ローカルにあるがProvider対応不明/変更 | update_watchlist.descriptionは公開資料・既存Requestにあるが最新Discoveryにない | 削除せず保持。Write実機確認は未許可のため未実施 |
| B：実行可能範囲に制約 | Alertのconditions、特定pattern extraのwebhook/monitorは既存Requestにあるが、公開説明では多条件/指標条件・webhook操作を制限 | 既存の制限説明を維持。Writeを試さず、型適合を成功保証としない |
| C：制約差 | OHLCV countのローカル上限5000に対し、最新Discovery説明はrows5000/columns8000。公開ページは5000のみ | columns限定8000へ拡張。5営業日windowでcount5001/8000指定を受理（取得5本） |
| C/F：制約・既定値の表現差 | live Schemaにはenum/上限/default等が省略される。ローカルNone既定とProvider既定は別概念 | 公開仕様/Discovery説明に根拠のあるenum等を維持。省略を無制限/同一の証拠としない |
| D：応答/エラー不一致 | 今回の範囲では修正を要する不一致なし。rows/listとcolumns/dict、追加カーソル、success=false、batch missing、経済カレンダーstatus/resultを現行包絡が保持 | Response/Client/エラーマッピングの変更不要。構造保持を全データの意味的検証とはしない |
| E：現行契約で対応可能 | 共通引数の型・必須性、Tool写像、指定値のみの直列化、追加応答保持、Read/Write方針 | 既存実装と回帰テストで確認 |
| F：未確認 | 個別未実行Tool、Write、全市場/全期間/全列、巨大応答、価格調整、他Provider障害条件 | 下表・実機節に範囲を記録。全35 Tool実行済みとはしない |

## 全35 Toolの照合表

Rは通常Read、R*はRead表記でも副作用があり非Retry、WはWrite・非Retry。wire名は[写像](../../src/tradingview_screening/integrations/tradingview/tool_catalog.py)とfixtureで全件一致を検証。引数欄はliveの全109引数。すべての共通フィールドで型/nullableと必須性を照合した。enum・上限等は後述の公開説明由来制約と比較する。

| Tool / wire | Policy | live引数（*は必須） | 分類・個別Read |
| --- | --- | --- | --- |
| `list_watchlists` / `mcp-watchlist-list-watchlists` | R | なし | E/F、個別未実施 |
| `get_watchlist` / `mcp-watchlist-get-watchlist` | R | `watchlist_id*` | E/F、個別未実施 |
| `get_active_watchlist` / `mcp-watchlist-get-active-watchlist` | R* | なし | E/F、個別未実施 |
| `create_watchlist` / `mcp-watchlist-create-watchlist` | W | `name`, `symbols` | E/F、個別未実施 |
| `delete_watchlist` / `mcp-watchlist-delete-watchlist` | W | `watchlist_id*` | E/F、個別未実施 |
| `add_to_watchlist` / `mcp-watchlist-add-to-watchlist` | W | `watchlist_id*`, `symbols*` | E/F、個別未実施 |
| `remove_from_watchlist` / `mcp-watchlist-remove-from-watchlist` | W | `watchlist_id*`, `symbols*` | E/F、個別未実施 |
| `update_watchlist` / `mcp-watchlist-update-watchlist` | W | `watchlist_id*`, `name` | B/F、description保持・Write未実施 |
| `get_ohlcv` / `mcp-tv-get-ohlcv` | R | `symbol*`, `interval`, `count`, `date_from`, `date_to`, `format`, `summary` | A/C修正、Read確認 |
| `get_economic_data` / `mcp-tv-get-economic-data` | R | `symbol*`, `date_from`, `date_to` | E/F、個別未実施 |
| `get_economic_symbols` / `mcp-tv-get-economic-symbols` | R | `country`, `category`, `search` | E、少量Read確認 |
| `search_symbols` / `mcp-tv-search-symbols` | R | `query*`, `type_filter` | E/F、個別未実施 |
| `get_symbol_data` / `mcp-tv-get-symbol-data` | R | `symbol*`, `columns` | E/F、個別未実施 |
| `run_screener` / `mcp-tv-run-screener` | R | `market`, `filters`, `sort_by`, `sort_order`, `limit`, `columns`, `symbol_types`, `filter_preset`, `symbolset` | E/F、個別未実施 |
| `get_symbol_data_batch` / `mcp-tv-get-symbol-data-batch` | R | `symbols*`, `columns` | E、少量Read確認 |
| `get_screener_columns` / `mcp-tv-get-screener-columns` | R | `market`, `group`, `search` | E/F、個別未実施 |
| `get_technicals_rating` / `mcp-tv-get-technicals-rating` | R | `symbol*`, `interval` | E/F、個別未実施 |
| `get_news` / `mcp-tv-get-news` | R | `symbol*`, `lang`, `limit`, `offset` | E、少量Read確認 |
| `get_news_story` / `mcp-tv-get-news-story` | R | `id*`, `lang`, `user_prostatus`, `user_country` | E/F、個別未実施 |
| `get_forecasts` / `mcp-tv-get-forecasts` | R | `symbol*` | E/F、個別未実施 |
| `get_financials` / `mcp-tv-get-financials` | R | `symbol*`, `metric`, `period` | E、少量Read確認 |
| `get_financial_history` / `mcp-tv-get-financial-history` | R | `symbol*`, `period`, `date_from`, `date_to` | E/F、個別未実施 |
| `get_documents` / `mcp-tv-get-documents` | R | `symbol*`, `category`, `event`, `start_date`, `end_date`, `limit` | E/F、個別未実施 |
| `get_document_view` / `mcp-tv-get-document-view` | R | `view_id*` | E/F、個別未実施 |
| `get_earnings_calendar` / `mcp-tv-get-earnings-calendar` | R | `symbols*`, `date_from`, `date_to` | E/F、個別未実施 |
| `get_economic_calendar` / `mcp-tv-get-economic-calendar` | R | `countries`, `currencies`, `category`, `date_from`, `date_to`, `min_importance` | E、少量Read確認 |
| `get_dividends_calendar` / `mcp-tv-get-dividends-calendar` | R | `symbols`, `market`, `date_from`, `date_to`, `limit` | E/F、個別未実施 |
| `create_alert` / `mcp-tv-create-alert` | W | `symbol*`, `price`, `condition`, `message`, `name`, `resolution`, `expiration`, `auto_deactivate`, `email`, `mobile_push`, `popup`, `conditions` | B/F、Write未実施 |
| `update_alert` / `mcp-tv-update-alert` | W | `alert_id*`, `message`, `name`, `expiration`, `auto_deactivate`, `email`, `mobile_push`, `popup` | B/F、Write未実施 |
| `delete_alert` / `mcp-tv-delete-alert` | W | `alert_ids*` | E/F、個別未実施 |
| `stop_alerts` / `mcp-tv-stop-alerts` | W | `alert_ids*` | E/F、個別未実施 |
| `restart_alerts` / `mcp-tv-restart-alerts` | W | `alert_ids*` | E/F、個別未実施 |
| `list_alerts` / `mcp-tv-list-alerts` | R | `symbol`, `active` | E/F、個別未実施 |
| `get_alerts` / `mcp-tv-get-alerts` | R | `alert_ids*` | E/F、個別未実施 |
| `get_alerts_log` / `mcp-tv-get-alerts-log` | R | `days`, `symbol`, `limit` | E/F、個別未実施 |

E/Fは入力主要契約は対応するが、そのToolの今回の個別実行は未確認という意味。Eだけの行も、実行節に示す少量Readの範囲を超える保証ではない。Watchlist・AlertのWrite 10個とget_active_watchlistは実行対象から除外した。

### 制約・既定値・指定形式

- 全35 Toolのrequired、primitive/array/items/object/nullable、additionalPropertiesとAlertのpatternPropertiesを照合。未知フィールドを無条件許可しない。既存の省略可能nullable契約は維持した。
- 公開資料/Discovery説明由来のenum/上限は`tests/schema_contract.py`のOVERLAYSに独立した事実として保持。Watchlist name500文字、batch50銘柄、Screener1000行、news200見出し、Alert name300/message4000文字、配当calendar200行、alert log2000件、importance -1〜1等を再照合した。
- OHLCV/technicalsのinterval、経済カテゴリ、銘柄種別、news言語、財務期間、文書カテゴリ/イベント、Screenerの6preset等の許容値を照合。marketはScreenerと列探索で別の名前空間。自由stringを「全て有効」と解釈しない。Screenerにoffset/pageを追加していない。
- Provider既定の主例はOHLCV interval=1D/count=300/format=rows、Screener america/volume/desc/100、列探索all、technicals 1D、news en/25、財務ttm・履歴fq、文書20、経済calendar US/importance=-1、配当calendar50、Alert cross/resolution=1、log7日/100件。Providerに委ねるためRequestへ既定値を注入しない。公開/Discoveryに未記載の既定値は未確認。
- 新日付引数は有効なYYYY-MM-DDか時差付きRFC3339。文字列を変換せず送信し、不正日付/時刻/時差、型違い、明示None、不明formatを拒否する。範囲の順序等について、根拠のない新制約は設けない。既存のcount下限も変更しない。
- 変更前の有効な呼出しは維持。新引数未指定は送信せず、既存フィールドの未指定と明示Noneを区別する。新3引数はstring非nullableなので明示Noneは拒否。構築後に不正に変更されたRequestも既存Clientで再検証する。

Responseは全35メソッドの戻り型を静的・テストで照合した。search_symbols/get_ohlcv/get_symbol_data/get_symbol_data_batch/get_screener_columns/run_screener/get_technicals_rating/get_economic_symbolsの8個はObservedReadResponse、それ以外27個はTypedToolResponse。共にcontentとstructured_contentを分け、追加フィールドを保持する。前者のsuccess/error/count/missing_countの安定フィールド型検証、Providerのsuccess=false、MCP is_error、不正Schema、通信例外の区別は現行契約を維持した。今回未実行の29 Toolの全出力構造・サービス成功は未確認。

## 少量Read実機確認

10/27 08:43〜08:44 JST、Discoveryを除き**6 Tool・15回**。success=true 13回、OHLCVの未知銘柄によるsuccess=false 1回、経済calendarのstatus=ok 1回。正常0件・部分欠損・Provider失敗を全件成功に置き換えていない。

OHLCVはすべて既存`client.get_ohlcv(GetOhlcvRequest(...))`で取得し、独自MCP/HTTPや汎用呼出しへ迂回していない。基本指定はsymbol=TSE:7203、interval=1D、summary=False。日付は2026年。

| OHLCV試験（10回） | 指定 | 観測・意味的確認 |
| --- | --- | --- |
| 互換 | 旧引数のみ、count=3 | rowsで3本、新引数を送らず成功 |
| 両端日付/rows | 10/05〜10/09、count=3、rows | 10/07〜10/09の最新3本、has_more=true |
| columns | 同じ日付/count、columns | t/o/h/l/c/vの配列。rowsの全OHLCV値と一致 |
| RFC3339 | 10/05T00:00:00Z〜10/09T23:59:59+00:00、count=3 | dateonlyのrowsと全値一致 |
| 開始のみ | date_from=10/08、count=2 | 10/23・10/26、開始以降の2本 |
| 終了のみ | date_to=10/09、count=2 | 10/08・10/09、終了以前で終端日を含む |
| 5000超 | 10/05〜10/09、columns、count=5001 | 5本、has_more=false |
| 8000指定 | 同じ5営業日window、columns、count=8000 | 同じ5本・全値一致。8000本の実取得試験ではない |
| カーソル | rows試験のnext_date_to=10/06T00:00:00Zをそのまま指定、開始10/05・count=3 | 残る10/05・10/06の2本。元3本と合成するとcolumnsの5本に全値一致・重複なし |
| Provider失敗 | 存在しないテスト用symbol、count=1 | success=false/error、足なし。成功0件に変換しない |

両端日付の包含、形式の一致、最新count本への制限、カーソル遡りを保存済み応答でassertした。全足のOHLCVは有限。価格調整、日中足、全期間、巨大応答、8000本全件、将来のカーソル形式は未検証。count_limitは今回の応答に出ておらず、上限数値の根拠はDiscovery説明と少量windowでの指定受理である。

| 他のRead（各1回） | 型付きRequest指定 | 結果・制約 |
| --- | --- | --- |
| get_symbol_data_batch | symbols=[TSE:7203,存在しないテストsymbol]、columns=[close] | success、count=1、missing_count=1。欠損を架空0へ変換せず保持 |
| get_financials | symbol=TSE:7203、metric=[pe]、period=ttm | success/dataをTypedToolResponseで保持。全財務の妥当性検証ではない |
| get_news | 同symbol、lang=ja、limit=1 | success/dataを保持。記事の権限・全文・全ページは未確認 |
| get_economic_symbols | country=JP、category=gdp | success、25項目。全経済カテゴリ/時系列の実行ではない |
| get_economic_calendar | countries=JP、10/01〜10/02、min_importance=1 | status=ok、result配列。successキー前提の一律判定を避ける |

認証・通信・Governorは既存のまま。初回Discovery取得後の説明表示のみcp932出力で失敗したが、構造と時刻の保存は完了していたため取得を重ねず、サニタイズ済み構造を利用した。資格情報やProviderの生応答をエラー文として表示していない。

## オフライン差分検出・回帰

[比較処理](../../tests/schema_contract.py)を既存テスト補助へ追加し、[開発専用実行例](../../scripts/development/compare_mcp_discovery.py)から利用する。実行時の型検証を動的Schemaへ置き換える機能、任意Toolの実行CLI、別の接続方式ではない。

リポジトリルートのコマンドプロンプトで：

```bat
call scripts\setenv.bat
"%PYTHON_EXECUTABLE%" scripts\development\compare_mcp_discovery.py tests\fixtures\tradingview_input_schemas_2026-10-27.json
```

Tool不足/追加、Request欠落、引数不足/余剰、required、型/nullable、enum/上下限/長さ等をパス付きJSONで報告する。Providerにdefaultがある場合はローカルとの差をdefault_reviewとして通知する。Providerのdefault省略は値が不明であり、Noneとの一致を保証しない。OVERLAYSは公開説明由来の既知差を照合するためのもので、新しい未知差分を自動修正しない。条件付き上限・日付妥当性・送信値は別の単体テストで確認する。

当日fixtureは35 Tool/109引数、ローカルは35 Request/110引数。残る診断は`update_watchlist.description: parameter_extra`の1件で、**比較コマンドはexit 1が期待値**。既知差を握り潰して全契約一致とはしない。構造差がなくdefault_reviewのみならexit 0でレビュー用情報を返す。任意JSON Schema全仕様の一般検証器ではなく、既存Discovery入力契約の検査である。

fixtureはname/inputSchemaの構造・型・必須性だけを抽出し、説明/title/examples・生市場データ・認証情報を除去した。未知Schema変更を入れたテストでTool/引数/required/型/nullable/enum/上限/長さ/default/Request不足の検出を確認する。既知のProvider成功失敗・追加フィールド保持・未知引数拒否・Read/Write Retry・Governor・OAuth回帰も対象とする。

プロジェクトEmbedded Pythonで次を実行し、合計**379 passed・1 skipped**。skipはWindowsでsymlinkを作成できない既存のパス逸脱検査1件で、検証失敗の置換ではない。pytestはWindows asyncioの内部ソケットを利用できるsandbox外で行い、外部Provider接続は上記のRead調査だけに限定した。

```bat
call scripts\setenv.bat
python -m pytest tests/test_schema_contract_audit.py tests/test_tradingview_typed_tools.py tests/test_tradingview_client.py -q
python -m pytest tests/test_tradingview_sdk_transport.py tests/test_tradingview_auth.py -q
python -m pytest tests/test_validation.py tests/test_public_screening_samples.py tests/test_screening_engine.py tests/test_jobs_cli.py -q
python -m pytest tests/test_request_governor.py -q
python -m ruff check src/tradingview_screening/integrations/tradingview/schemas.py tests/schema_contract.py tests/test_tradingview_typed_tools.py tests/test_schema_contract_audit.py scripts/development/compare_mcp_discovery.py
git diff --check
```

順に203 passed、22 passed、115 passed/1 skipped、39 passed。ruff・diff checkも合格。新引数の直列化/省略・明示None・不正値、rows/columns上限、追加応答保持、全Toolの写像/Read-Write方針、Governor、OAuth/SDK transport、既存Screening/Jobを回帰確認した。文書の相対リンク/アンカー77件とPython例2件の構文、全35 Tool表・fixtureの引数件数も静的検証した。

無関係な全件pytest・Docker再buildは実施しない。CLI/BAT/既存Screening JSON/Job/認証・通信制御/Watchlist同期/依存関係を変更しない。既存未追跡tradingview_container_test/は保持する。

## PR #63へ後から反映する内容

今回PR #63のファイルは取り込まない。既存FEATURESのOHLCV説明と開発API/仕様書を最小限更新した。後日PR #63がdevelopへ反映されたら、その時点の実装と再照合して以下を更新する。

1. OFFICIAL_MCP_MANUALのGetOhlcvRequest引数行を7行にし、date_from/date_to/format、rows5000/columns8000、応答レイアウトと指定省略互換性を説明する。
2. 「OHLCV追加引数はラッパー未対応」という差分を解消済みに変更する。公開ページには追加引数がまだなく、Discoveryと実機が根拠である点は残す。
3. update_watchlist.descriptionの公開資料/Discovery不一致とWrite未検証を維持する。
4. SMA25等のローカル計算では、選んだformatの実応答を読む。日付指定対応を確定足・価格調整・全プライム完全性の保証としない。条件カタログのfilter対応状況は今回変更しない。

配布は別工程で必要になった場合だけ、developレビュー/merge後の配布対象コミットのみcherry-pick -x等で選択する。本記録・tests・fixture・開発比較スクリプトはmainへ取り込まない。
