# AIからの共通CLI利用

Repository rootで共通CLIを使います。Windowsでは`app.bat`がEmbedded Pythonを選択します。JobごとのBATや、AIからMCP SDKへの独自呼出しは追加しません。

```bat
app.bat jobs list
app.bat run sample_screen_daily
app.bat schedule list
app.bat schedule apply
app.bat schedule remove sample_screen_daily
```

`jobs list`で定義・参照を検証してから、明示されたJobを実行します。`run`はenabled=falseでも実行します。saveとwatchlistSyncはJob設定に従います。Watchlist同期は実Writeなので、ユーザーの依頼範囲と設定を確認してください。所有権は`.local/managed_watchlists.json`の保存IDのみで、同名の既存Watchlistを採用しません。

stdoutはJSON 1つ、stderrは診断です。exit 0でもpartialやalready_runningの可能性があるため、status/errors/metadataを併せて確認してください。runtime failureは1、usage/configは2、AUTH_REQUIREDは3です。raw Provider応答やtokenを表示・保存しないでください。

AUTH_REQUIREDはpartialのときもexit 3を優先します。未実装builtinやSchedulerのunsupportedはexit 1です。

## 米国セクターbuiltin

`results latest`はScreening結果用です。builtin保存結果はJob JSONの相対resultPathで参照します。

Phase 9の`us_sector_daily`は、`america / stock`全Universeのsector/changeを1 symbol = 1票で集計する契約です。sample Jobは`us_sector_morning`、07:00 JST。`meanChange`は算術平均、`sampleSize`は有効unique symbol数。同率はcompetition ranking（1, 1, 3）とsector名昇順。同値重複は1票、矛盾は失敗、欠損は除外し、不正型を欠損扱いしません。

**2026-10-18の再検証でもProvider制約により全Universe取得とlive保存は未達です。** sector/change列のstock対応とS&P 500限定の少量取得は確認できましたが、条件なし取得はProviderが拒否しました。公式schemaは上限1000件で、pagination・完全partition契約は未確認です。先頭1000件を全米株として表示したり、S&P 500やNASDAQ、任意filterへ変更して実行成功を作ったりしないでください。

full coverageを安全に確認できるまでliveの`app.bat run us_sector_morning`は実行しません。確認できた後は共通CLIを使用します。成功応答の件数不足は`US_SECTOR_COVERAGE_INCOMPLETE`で保存せず停止します。取得・列確認は同一Clientと既存RequestGovernor経由です。builtinのwatchlistSync=trueは設定エラーで、Watchlist Writeは行いません。

米国regular session終了後のsnapshotを使う運用前提はsessionAssumptionに記録し、retrievedAtを必ず確認してください。休日・早期終了判定やOHLCV再計算はなく、集計へニュース解釈・投資判断を追加しません。詳細は[Results](RESULTS.md)を参照してください。Windows導入は別PR #21、一般Screening拡張は別PR #23で管理します。

## Jobの排他とTask

同一Jobは全実行期間をfilelockで保護します。二重起動は待機せずalready_running/exit 0です。失敗後にWriteを自動再送・rollbackせず、確定済み結果とエラーを確認します。

Taskは`TradingViewMcpSupport__<job_name>`です。applyは有効Jobの作成/更新だけを行い、disabled・定義消失による削除はしません。削除はremoveの完全一致だけです。既存ユーザーTaskをテストに流用しないでください。

SchedulerはWindows通常ユーザーのログオン中に実行し、保存済みOAuth tokenとrefreshだけを使います。認証切れ時にブラウザ・DCR・mcp authを自動起動しません。対応timezoneはdailyのAsia/Tokyo（明示+09:00）のみで、他IANA/DSTをローカル時刻へ読み替えません。

`screen`、`results latest`、`mcp auth/status/tools`は引き続き利用できます。詳しくは[Schedule Manual](SCHEDULE_MANUAL.md)、[Screening Manual](SCREENING_MANUAL.md)、[Watchlist Sync](WATCHLIST_SYNC.md)を参照してください。
