# AIから共通CLIを使う

AIアプリでこのリポジトリを開き、展開フォルダから共通`app.bat`を実行するよう依頼します。別のTradingView connectorや独自スクリプトを用意する必要はありません。初回導入は先に[Windows導入](WINDOWS_SETUP.md)を完了してください。

## Read-onlyの依頼例

> jobs listで定義を確認し、public_sample_screen_dailyを実行してください。保存されたsample_standard_screenの最新結果と直近10件の履歴を表示してください。Watchlist・AlertのWrite、Scheduler登録・削除は行わないでください。

対応するコマンドは次のとおりです。

```bat
app.bat jobs list
app.bat run public_sample_screen_daily
app.bat results latest sample_standard_screen
app.bat results history sample_standard_screen --limit 10
```

TradingViewへのReadとPC内へのJSON保存です。`enabled=false`でも手動runは実行します。Job名ではなくScreening名で履歴を取得する点に注意してください。

## 前回差分を確認する

> 保存済みsample_standard_screenの直近2件を比較してください。条件のfingerprintとcoverageを確認し、比較できなければ理由を説明してください。データの新規取得は不要です。

```bat
app.bat results compare sample_standard_screen
```

この操作はローカル読み取りだけです。1件以下なら`NO_BASELINE`、条件変更・旧形式などなら比較不能となります。比較可能な古いペアへ差し替えたり、古い結果へ現在のfingerprintを付け足したりしません。

`observed_set_only`なら「今回未観測」と説明し、条件に不適合になったとは断定しません。`totalCount`はProvider総該当件数、`returnedCount`は実取得行数です。詳細は[結果マニュアル](RESULTS.md)を参照してください。

## Write・登録・削除を依頼する場合

Watchlist同期やScheduler登録は利用者が対象と副作用を理解して明示依頼する場合だけ行います。[Watchlist](WATCHLIST_SYNC.md)と[Scheduler](SCHEDULE_MANUAL.md)で操作を先に確認してください。`sample_screen_daily`は実Writeを伴い、`schedule apply`は有効な全Jobを登録・更新します。

## AIが確認する出力

通常のstdoutはJSON、stderrは診断です。終了コード0でも部分成功や重複実行スキップの場合があるため、`status`、`errors`、`metadata`を確認します。終了コード1は実行時失敗、2は引数・定義不正、3は再認証要求です。

token・認可code・credential・Providerの生応答全文をチャットへ貼り付けないでください。失敗したWriteの自動再送やrollbackをせず、確認済みの結果を報告します。

全米株集計は現在未対応です。`us_sector_morning`を実行して成功を作ろうとしたり、S&P 500や先頭1000件へ範囲を狭めて全米株結果と説明したりしません。

[CLIの技術契約](../development/CLI_CONTRACT.md) / [トラブル対応](TROUBLESHOOTING.md) / [利用者マニュアル一覧](README.md)
