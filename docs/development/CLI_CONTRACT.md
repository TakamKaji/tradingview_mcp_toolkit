> **開発者向け：CLI・Job・builtinの運用契約**。一般のAI利用手順は[AIからのCLI利用](../user/AI_USAGE.md)へ分離しました。本文のPhaseと実測は当時の境界を示します。

# AIからの共通CLI利用

Repository rootで共通CLIを使います。Windowsでは`app.bat`がEmbedded Pythonを選択します。JobごとのBATや、AIからMCP SDKへの独自呼出しは追加しません。

Windowsの初回導入は[Windows Setup](../user/WINDOWS_SETUP.md)を参照してください。

```bat
app.bat jobs list
app.bat run public_sample_screen_daily
app.bat run sample_screen_daily
app.bat schedule list
app.bat schedule apply
app.bat schedule remove sample_screen_daily
```

`jobs list`で定義・参照を検証してから、明示されたJobを実行します。`run`はenabled=falseでも実行します。初回確認は`public_sample_screen_daily`を優先してください。このJobはenabled=false / save=true / watchlistSync=falseで、結果をローカル保存しますがTradingView WatchlistへWriteせず、`schedule apply`でも登録されません。`sample_screen_daily`はWatchlist同期を行う運用サンプルです。saveとwatchlistSyncはJob設定に従います。Watchlist同期は実Writeなので、ユーザーの依頼範囲と設定を確認してください。所有権は`.local/managed_watchlists.json`の保存IDのみで、同名の既存Watchlistを採用しません。

stdoutはJSON 1つ、stderrは診断です。exit 0でもpartialやalready_runningの可能性があるため、status/errors/metadataを併せて確認してください。runtime failureは1、usage/configは2、AUTH_REQUIREDは3です。raw Provider応答やtokenを表示・保存しないでください。

AUTH_REQUIREDはpartialのときもexit 3を優先します。未実装builtinやSchedulerのunsupportedはexit 1です。

同一Jobは全実行期間をfilelockで保護します。二重起動は待機せずalready_running/exit 0です。失敗後にWriteを自動再送・rollbackせず、確定済み結果とエラーを確認します。

Taskは`TradingViewMcpSupport__<job_name>`です。applyは有効Jobの作成/更新だけを行い、disabled・定義消失による削除はしません。削除はremoveの完全一致だけです。既存ユーザーTaskをテストに流用しないでください。

SchedulerはWindows通常ユーザーのログオン中に実行し、保存済みOAuth tokenとrefreshだけを使います。認証切れ時にブラウザ・DCR・mcp authを自動起動しません。対応timezoneはdailyのAsia/Tokyo（明示+09:00）のみで、他IANA/DSTをローカル時刻へ読み替えません。

`screen`、`results latest`、`mcp auth/status/tools`は引き続き利用できます。詳しくは[Schedule Manual](../user/SCHEDULE_MANUAL.md)、[Screening Manual](../user/SCREENING_MANUAL.md)、[Watchlist Sync](WATCHLIST_SYNC.md)を参照してください。

## 米国セクターbuiltin

`results latest`はScreening結果用です。builtin保存結果はJob JSONの相対resultPathで参照します。

Phase 9の`us_sector_daily`は、`america / stock`全Universeのsector/changeを1 symbol = 1票で集計する契約です。sample Jobは`us_sector_morning`、07:00 JST。`meanChange`は算術平均、`sampleSize`は有効unique symbol数。同率はcompetition ranking（1, 1, 3）とsector名昇順。同値重複は1票、矛盾は失敗、欠損は除外し、不正型を欠損扱いしません。

**2026-10-18の再検証でもProvider制約により全Universe取得とlive保存は未達です。** sector/change列のstock対応とS&P 500限定503銘柄・20分類の集計、JSON保存・読み戻しを実機確認しましたが、全米株の条件なし取得はProviderが拒否しました。公式schemaは上限1000件で、pagination・完全partition契約は未確認です。先頭1000件を全米株として表示したり、S&P 500やNASDAQ、任意filterへ変更して実行成功を作ったりしないでください。

`app.bat run us_sector_morning`は2026-10-18の実機テストでProvider失敗・保存なしでした。全米株のfull coverageを安全に確認できるまで、同梱Jobはenabled=falseで定期登録しません。確認できた後は共通CLIを使用します。成功応答の件数不足は`US_SECTOR_COVERAGE_INCOMPLETE`で保存せず停止します。取得・列確認は同一Clientと既存RequestGovernor経由です。builtinのwatchlistSync=trueは設定エラーで、Watchlist Writeは行いません。

米国regular session終了後のsnapshotを使う運用前提はsessionAssumptionに記録し、retrievedAtを必ず確認してください。休日・早期終了判定やOHLCV再計算はなく、集計へニュース解釈・投資判断を追加しません。詳細は[Results](RESULTS.md)を参照してください。

## ローカル履歴と前回比較

```bat
app.bat results history public_japan_value --limit 10
app.bat results compare public_japan_value
```

この2コマンドは保存済みJSONだけを読みます。実行前後に認証・MCP接続・Job・Watchlist同期・Scheduler操作を追加する必要はありません。差分ファイルを自動保存せず、既存結果も変更しません。

比較は同名の直近2件の成功snapshotを選び、その後で定義fingerprintと入力を検証します。結果不足、fingerprint欠落・不一致・未対応形式、不正symbol・重複等を検出したら理由を報告してください。比較可能な古い結果を探して「前回との差分」と表示しないでください。旧結果へ現在の定義からfingerprintを後付けしません。

差分の呼び方は `observedAdded` / `observedRemoved` とし、coverageが不完全または不明なら「観測集合への出現・今回未観測」と説明します。順位やlimitで見えなくなった可能性があり、条件適合・失格とは断定しません。ProviderのtotalCountと実取得returnedCountは分けて表示します。具体的なJSON契約は[Results](RESULTS.md)を参照してください。
