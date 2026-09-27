# AIからの共通CLI利用

Repository rootで共通CLIを使います。Windowsでは`app.bat`がEmbedded Pythonを選択します。JobごとのBATや、AIからMCP SDKへの独自呼出しは追加しません。

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

`screen`、`results latest`、`mcp auth/status/tools`は引き続き利用できます。builtinの本体とPhase 9米国セクター集計は未実装です。Windowsの初回導入は[Windows Setup](WINDOWS_SETUP.md)、Job運用は[Schedule Manual](SCHEDULE_MANUAL.md)、Screeningは[Screening Manual](SCREENING_MANUAL.md)、書き込みを伴う同期は[Watchlist Sync](WATCHLIST_SYNC.md)を参照してください。
