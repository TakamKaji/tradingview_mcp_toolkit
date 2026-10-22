# AIから共通CLIを使う

AIには展開フォルダで共通`app.bat`を使うよう依頼します。通常のScreening・結果管理・Job実行に、別のTradingView connectorや条件ごとのPythonスクリプトは不要です。初回導入は[Windows導入](WINDOWS_SETUP.md)を完了してください。

## 共通機能と依頼範囲を確認する

[機能一覧](FEATURES.md)のとおり、CLIは定義済みScreeningの実行、結果の参照、Job、Scheduler、MCP認証・一覧確認を扱います。公式Toolの全操作を任意に呼ぶCLIではありません。ローソク足・ニュース・財務のPythonラッパーがあっても、それを取得・定期保存するJobがあるとは説明しないでください。

## 会話からScreeningを作成し、方式を選ぶ

ChatGPT・Codexのどちらでも、最初に[AIによるScreening生成ガイド](AI_JSON_GUIDE.md)と実際のSchema・公式Provider対応項目・サンプルを読み、希望を整理します。公開URLだけで必ず本文を読めるとは限らないため、アクセスできなければ必要資料を渡してください。

- **方式A（最優先）**：単一Screeningで表現できれば`screenings/*.json`を作り、Jobが必要な場合だけ`jobs/*.json`も作ります。通常の条件に独自Python・BATを追加しません。
- **方式B**：ランキング確定後の別時間足判定や外部母集団との照合など、単一JSONで表現できない処理だけPythonを選び、理由を説明します。既存の公式MCPクライアント・認証・通信制御・互換性のある保存・Watchlist安全機構を再利用します。汎用pipelineエンジンや複合処理専用CLIはなく、Pythonファイルを標準`screen`やJobの参照先に指定しても動きません。

ChatGPTは完成ファイルと保存手順を提供し、通常チャットから利用者PCへ自動設置しません。Codexはアクセス可能なローカル環境へ保存・検証します。Python方式では実際の保存先・依存・実行環境・起動方法・結果形式を明示します。外部データの出典・取得時刻・欠損・制限を示し、不完全な結果を全件取得と報告しません。

ファイル作成・ローカル検証・実取得・Writeは別操作です。利用者から指示されない限りTradingViewへの実書き込みやScheduler登録・削除を実行しません。以下のCLI例は方式Aに対する操作です。

## 自分の条件・Jobを作る依頼例

> public_japan_value.jsonを別名のmy_japan_value.jsonへコピーし、nameも一致させてください。日本株、PER 0〜15、予想配当利回り3%以上、出来高降順、limit 20、Watchlist無効にします。JSONを確認し、既存サンプルは変更しないでください。

全文と許可される設定は[Screeningマニュアル](SCREENING_MANUAL.md#自分の条件を追加する)を参照します。定期実行も必要なら、[Jobの作成手順](SCHEDULE_MANUAL.md#自分のjobを作る)に従い別名のJobを作り、最初は`enabled=false`・`watchlistSync=false`で手動確認します。定義作成とTask登録は別の依頼です。

## Read-only実行の依頼例

上のScreeningを作成してから、次のように依頼できます。

> my_japan_valueをscreenで実行し、最新結果と直近10件の履歴を表示してください。Watchlist・Alert WriteとScheduler登録・削除は行わないでください。

```bat
app.bat screen my_japan_value
app.bat results latest my_japan_value
app.bat results history my_japan_value --limit 10
```

TradingView ReadとPC内への保存です。Jobを作った場合は`run my_japan_value_daily`で実行しますが、結果参照には引き続きScreening名`my_japan_value`を使います。`enabled=false`でも手動runは実行します。

## 前回差分を確認する

> 保存済みmy_japan_valueの直近2件を比較してください。条件のfingerprintとcoverageを確認し、比較できなければ理由を説明してください。新規取得は不要です。

```bat
app.bat results compare my_japan_value
```

ローカル読み取りのみです。1件以下は`NO_BASELINE`、条件変更・旧形式等は比較不能です。古い比較可能ペアへの差し替えや、旧結果へのfingerprintの後付けは行いません。`observed_set_only`なら「今回未観測」と説明し、条件不適合と断定しません。Provider総件数`totalCount`と実取得行数`returnedCount`を区別します。

## 同梱例で試す場合

同梱JSONは共通機能の使用例です。Jobの初回試用を依頼するなら`public_sample_screen_daily`を指定できます。これはRead-only＋ローカル保存で、結果名は`sample_standard_screen`です。`sample_screen_daily`は別のWrite付き例なので、名前を取り違えないでください。

## Write・登録・削除を依頼する場合

利用者が対象と副作用を理解して明示依頼する場合だけ行います。[Watchlist](WATCHLIST_SYNC.md)と[Scheduler](SCHEDULE_MANUAL.md)を先に確認します。`schedule apply`は**有効な全Job**を登録・更新するため、自分のJobだけでなく同梱の`sample_screen_daily`も点検してください。無効化だけでは既存Taskは削除されません。

## 出力と失敗時

stdoutはJSON、stderrは診断です。exit 0でも部分成功・重複スキップがあり、`status`、`errors`、`metadata`を確認します。exit 1は実行時失敗、2は引数・定義不正、3は再認証要求です。

token・認可code・credential・Providerの生応答全文をチャットへ貼りません。Write失敗を自動再送・rollbackせず、確認済み結果を報告します。全米株の条件なし取得は公式Providerが拒否するため、S&P 500や先頭1000件へ縮小して全米株成功と説明しないでください。

[結果の読み方](RESULTS.md) / [トラブル対応](TROUBLESHOOTING.md) / [利用者マニュアル一覧](README.md)
