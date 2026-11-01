# 保存結果・履歴・前回差分を見る

結果の読み取りはPC内の保存JSONだけを使います。TradingViewへの接続や認証、Watchlist更新、Scheduler操作は行いません。

任意の名前付きScreeningで共通して使える機能です。以下は[作成手順](SCREENING_MANUAL.md#自分の条件を追加する)の`my_japan_value`を実行・保存した後の例で、別の条件では自分のScreening名へ読み替えます。

## 最新結果を見る

```bat
app.bat results latest my_japan_value
```

結果はJob名ではなくScreening名で検索します。名前を省略した`app.bat results latest`は、すべてのScreeningから最新を探します。有効な結果がなければエラーになります。

`screen`と保存を有効にしたJobの成功結果は`results/YYYY-MM-DD/`に入ります。時刻はAsia/Tokyo、同じ秒の実行は連番で保存され、既存結果を上書きしません。失敗は保存しません。`results/`はGit管理外なので、必要な履歴は利用者がバックアップしてください。

米国セクターbuiltinの保存形式は別で、`results latest/history/compare`の対象ではありません。全米株の条件なし取得は**TradingView公式MCP Providerが拒否**するため、誤った全米株集計を避ける目的で対象Jobを無効にしています（[実測と制限](SCREENING_MANUAL.md#公式mcp-beta版のスクリーニング制限2026-10-18実機確認)）。

## 履歴を見る

```bat
app.bat results history my_japan_value --limit 10
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
app.bat results compare my_japan_value
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

履歴・比較は既存結果を移行・削除せず、差分ファイルも自動保存しません。保存形式は[results.py](../../src/tradingview_screening/screening/results.py)で確認できます。

## 保存JSONからCSV・HTMLを作る（任意の後変換）

**JSONが正本で、CSV・HTMLは同じ保存JSONから必要なときだけ作る閲覧用ファイルです。** 元のJSON・履歴・fingerprintは変更しません。変換のためにTradingViewへ再接続せず、認証もWatchlistへの書き込みも発生しません。

ファイルは既存の`results/YYYY-MM-DD/<Screening名>_HHMMSS.json`を指定します。パスとファイル名は`results history <Screening名>`で確認できます。以下の`2026-10-22`と`153000`はファイル名の書き方の例で、実際の保存ファイルへ読み替えてください。

### Windows

```bat
export-results.bat "results\2026-10-22\my_japan_value_153000.json" --format csv
export-results.bat "results\2026-10-22\my_japan_value_153000.json" --format html
export-results.bat "results\2026-10-22\my_japan_value_153000.json" --format csv --lang en
export-results.bat "results\2026-10-22\my_japan_value_153000.json" --format html --lang en
```

**表示言語は日本語（`ja`）が既定で、`--lang en`で英語を選べます。** 省略時または`--lang ja`では同じ場所に`my_japan_value_153000.csv`・`my_japan_value_153000.html`、英語指定では`my_japan_value_153000.en.csv`・`my_japan_value_153000.en.html`を生成します。`--output 保存先ファイル`を指定した場合は、そのパスを優先し、言語サフィックスを自動追加しません。

CSVはExcelで開きやすいUTF-8 BOM付きです。`--lang`で列見出しだけを選び、取得値は翻訳せず、列順・行順も変えません。未知のフィールド名は元キーを表示し、翻訳後の見出しが衝突する場合も識別できるようにします。数式として解釈される危険な文字列・見出しには安全対策としてアポストロフィを付けますが、数値型の負数には付けません。元JSONの値は変更しません。

HTMLは上部の**「日本語 / English」**で、生成した1ファイル内の列見出し・メタデータ項目名・ステータス・注意事項・フッターを切り替えられます。`--lang`は初期表示の指定で、どちらで生成しても両言語へ切り替え可能です。切り替えに外部通信・再生成・Webサーバーは不要です。HTMLの銘柄コード欄からTradingViewチャートを開くリンクは、押したときだけ外部サイトへアクセスします。

既存の出力を置き換えるときだけ`--overwrite`を明示してください。`--output`・`--overwrite`でも元JSONへの上書きはできません。ホストPCへの追加Python導入は不要で、`setup.bat`が準備する同梱Pythonを使います。

### Docker

Dockerでは結果JSONはホストの`results/`ではなく、専用volumeの`/workspace/results/`に保存されています。既存コンテナから変換するときは次の形式で実行します。

```sh
docker compose -f compose.docker.yml run --rm --entrypoint python app -m tradingview_screening.export_results /workspace/results/2026-10-22/my_japan_value_153000.json --format html
docker compose -f compose.docker.yml run --rm --entrypoint python app -m tradingview_screening.export_results /workspace/results/2026-10-22/my_japan_value_153000.json --format csv --lang en
```

Dockerでも`--lang ja|en`、`--output`、`--overwrite`は同じ指定です。出力は同じDocker volume内なので、ホストでファイルが必要なら[Dockerマニュアルのバックアップ手順](DOCKER.md#終了再実行更新バックアップ)に従って取り出してください。

### 対応する結果・注意点

- 現行の標準Screening結果のほか、`status=success`または`partial`かつ`results`がオブジェクト配列の独自複合処理JSONにも対応します。配列内のキーを全件調べて表の列にします。
- `partial`は成功扱いの全件結果として表示せず、HTMLに注意書きを表示します。`failed`は変換を拒否します。CSVには結果行だけを出し、実行日時・coverage・取得範囲等の正本メタデータは元JSONに残ります。
- 独自形式の`top100`などの補助配列はCSV/HTMLに自動出力しません。表示対象は`results`配列です。
- **Watchlist同期はCSV/HTMLへの変換とは別のWrite操作**です。既存のScreening Jobを明示的に実行する場合だけ同期します。保存済みJSONを任意に選んで直接Watchlistへ同期する機能は追加しません。
- この変換はファイル形式の変更だけで、データ欠損やProvider制約を解決するものではありません。

## 同梱サンプルの場合

`public_japan_value_daily`の結果は`public_japan_value`、`public_sample_screen_daily`と`sample_screen_daily`の結果は`sample_standard_screen`で参照します。`my_japan_value_daily`を自作した場合は`my_japan_value`です。サンプル専用の履歴機能ではありません。

ローソク足・ニュース等の任意Python API応答はこのScreening結果の保存・比較には接続していません。[機能の対応範囲](FEATURES.md)を参照してください。

[トラブル対応](TROUBLESHOOTING.md) / [利用者マニュアル一覧](README.md)
