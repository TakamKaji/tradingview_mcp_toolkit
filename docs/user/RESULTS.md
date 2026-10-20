# 保存結果・履歴・前回差分を見る

結果の読み取りはPC内の保存JSONだけを使います。TradingViewへの接続や認証、Watchlist更新、Scheduler操作は行いません。

## 最新結果を見る

```bat
app.bat results latest sample_standard_screen
```

`public_sample_screen_daily`の保存結果名は`sample_standard_screen`です。Job名をそのまま指定しないでください。名前を省略した`app.bat results latest`は、すべてのScreeningから最新を探します。有効な結果がなければエラーになります。

`screen`と保存を有効にしたJobの成功結果は`results/YYYY-MM-DD/`に入ります。時刻はAsia/Tokyo、同じ秒の実行は連番で保存され、既存結果を上書きしません。失敗は保存しません。`results/`はGit管理外なので、必要な履歴は利用者がバックアップしてください。

米国セクターbuiltinの保存形式は別で、`results latest/history/compare`の対象ではありません。全米株の条件なし取得は**TradingView公式MCP Providerが拒否**するため、誤った全米株集計を避ける目的で対象Jobを無効にしています（[実測と制限](SCREENING_MANUAL.md#公式mcp-beta版のスクリーニング制限2026-10-18実機確認)）。

## 履歴を見る

```bat
app.bat results history sample_standard_screen --limit 10
```

日付フォルダをまたいで新しい順に列挙します。`--limit`は既定20、1〜1000です。0件のときは空の`items`で正常終了します。

| 表示 | 意味 |
| --- | --- |
| executedAt / file | 実行日時・保存ファイルの識別情報 |
| returnedCount | 実際に取得した行数 |
| totalCount | Providerが返した、その条件に該当する総件数 |
| completeCoverage | 指定した条件内の全件が取得できたか |
| definitionFingerprint | 実行条件を識別する値（旧形式は未記録） |

例えば`totalCount=503`、`returnedCount=5`は503件中5件を取得した意味で、全件取得ではありません。`completeCoverage=true`でも、その条件・Universe内の一致であり市場全体の保証ではありません。古い保存結果で未記録の項目は`null`になります。

## 直前の結果と比較する

```bat
app.bat results compare sample_standard_screen
```

直近2件の成功結果を比較し、次のJSONを返します。古い方が`from`、新しい方が`to`です。

| 表示 | 意味 |
| --- | --- |
| observedAdded | 今回新しく観測された銘柄 |
| observedRemoved | 今回観測されなかった銘柄 |
| observedCommon | 両方で観測された銘柄 |
| indicatorChanges | 共通銘柄の指標値の変化 |
| totalCountChange | Provider総該当件数の差 |
| comparisonScope | 全該当集合か、取得した観測集合だけの比較か |

両結果の`completeCoverage=true`を確認できれば`full_matched_set`、それ以外は`observed_set_only`です。後者では順位や取得上限の影響があるため、`observedRemoved`を「条件に不適合になった」「銘柄が脱落した」と断定できません。総該当件数の差と取得済み銘柄数の差も別の値です。

## 比較できない場合

同じ名前でも、filter・market・limit・取得列など実行条件が異なる場合は比較しません。条件はversion付きSHA-256のfingerprintで識別します。旧形式に現在の条件を後付けしたり、古い比較可能なペアを探して「前回」とすることはありません。

| reason | 対応 |
| --- | --- |
| NO_BASELINE | 成功結果が2件未満。同じ条件で次回の結果を保存してから比較 |
| DEFINITION_MISMATCH | 直近2件の実行条件が異なる。新しい同条件の結果が2件揃うまで待つ |
| MISSING_FINGERPRINT | 旧形式などで条件を確認できない。既存ファイルを改変せず、新しい結果を蓄積 |
| INVALID_FINGERPRINT / UNSUPPORTED_FINGERPRINT | 不正・未対応形式。元ファイルを保持して診断 |
| INVALID_SYMBOLS / INVALID_VALUES / INVALID_METADATA | 重複銘柄、対象外の値、件数不整合など。元ファイルを保持して診断 |

比較不能は`status=not_comparable`、終了コード1です。初回の`NO_BASELINE`は想定された結果です。壊れたJSONや危険なリンクは候補から除外されますが、直近2件として選ばれた結果の条件不一致などは飛ばしません。

履歴・比較は既存結果を移行・削除せず、差分ファイルも自動保存しません。詳細な[JSON契約と架空データ例](https://github.com/TakamKaji/tradingview_mcp_support/blob/develop/docs/development/RESULTS.md)は開発者向け資料にあります。

[トラブル対応](TROUBLESHOOTING.md) / [利用者マニュアル一覧](README.md)
