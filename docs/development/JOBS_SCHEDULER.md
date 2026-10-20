# Job実行とWindows Task Scheduler

Jobは`jobs/<job_name>.json`へ追加します。共通`app.bat`と`setenv.bat`がプロジェクト内のEmbedded Pythonを選ぶため、Job別BATやシステムPythonは不要です。

```bat
app.bat jobs list
app.bat run public_sample_screen_daily
app.bat run sample_screen_daily
app.bat schedule apply
app.bat schedule list
app.bat schedule remove sample_screen_daily
```

Python環境からは`python -m tradingview_screening`に同じ引数を渡せます。Repository rootから実行してください。非WindowsでのScheduler操作は明示エラーです。

## Job定義

初回確認用は`jobs/public_sample_screen_daily.json`です。enabled=false / save=true / watchlistSync=falseのため、手動runはできますがTask Schedulerへ登録されず、TradingView Watchlistにも書き込みません。`jobs/sample_screen_daily.json`はsave/watchlistSyncともにtrueの運用サンプルです。filenameと内部nameを一致させ、task.definitionにScreening名を指定します。Screening側もfilename/internal nameを一致させます。一覧は名前順で、壊れたJSON・不正定義・参照不正が1つでもあれば全体を失敗（exit 2）にします。

- `enabled`はSchedulerへの登録可否です。明示的な`run`はfalseでも実行できます。
- `output.save=true`で標準Screening結果を`results/YYYY-MM-DD/`へ保存します。falseでは保存しません。
- `output.watchlistSync=true`で正常なScreening結果をPhase 7の管理Watchlist同期へ渡します。falseではWatchlist Toolを呼びません。Screening側のwatchlist無効設定も尊重します。
- Watchlist所有権は保存済みIDのみです。同名の既存Watchlistを採用しません。正常0件は管理Watchlistから全銘柄をremoveするため、条件を確認してください。[同期契約](WATCHLIST_SYNC.md)
- `builtin`の`us_sector_daily`はPhase 9で実装されています。未知builtinは`JOB_TASK_UNAVAILABLE`、builtinで`watchlistSync=true`は設定エラーです。全米株の条件なし取得は現行公式MCPが拒否するため、`us_sector_morning`サンプルはenabled=falseです。

## 多重起動と結果

手動CLIもTask Schedulerも同じJob Runnerを使います。同一JobのScreening・保存・Watchlist同期が終わるまで、`.local/job_locks/<sha256(job_name)>.lock`を保持します。Phase 7のWatchlist lockとは別です。異なるJobは独立して実行できます。

競合時は待たずに`status=success`、`metadata.skipped=true`、`reason=already_running`、exit 0を返します。権限・path等のlock故障は競合と区別します。残っているlockファイルだけで実行中とは判断できません。

stdoutは`operation=job`のJSONを1つ返します。Screeningの保存結果とは別のEnvelopeです。保存の有無と相対resultPath、Watchlist同期の確定結果、errorsを確認してください。stderrは人間向け診断です。

| 状態 | exit |
| --- | --- |
| success / partial / already_running | 0 |
| Provider・保存・Scheduler等のruntime failure | 1 |
| usage / config validation | 2 |
| AUTH_REQUIRED | 3 |

下位failedやstep例外をJob successへ変更しません。下位partialはJob partialです。正常Screening以外をWatchlistへ渡さず、保存失敗後の同期も行いません。途中まで成功していても、後続stepの失敗と確定済み結果を区別します。自動rollbackやWrite再送はしません。

errorsにAUTH_REQUIREDがあればpartialでもexit 3を優先します。未実装builtinとSchedulerのunsupportedは実行時エラー（exit 1）です。

## Task登録と削除

管理対象はTask Schedulerルートの`TradingViewMcpSupport__<job_name>`です。`apply`は全定義と有効Jobの実行可否・timezoneを事前検証し、有効Jobを同じTask名へ作成/更新します。同設定の再適用も安全なupdateとして扱えます。

disabledやJSON削除によるTaskの自動削除はありません。既存Taskを止めたい場合は`remove <job_name>`を明示してください。Job JSONが削除済みでも、安全なJob名なら完全一致Taskを削除できます。不在も機械可読な結果です。Prefix外Taskやワイルドカード削除は扱いません。

登録途中に失敗した場合は完了済み操作を返してfailedにします。自動rollbackはありません。`list`で管理Taskを確認してから必要な操作を行ってください。

## Windowsユーザーと認証

Windows PowerShell経由でTask Scheduler COMを操作します。ローカライズされたコマンド出力の解析や、追加Python依存は使いません。Taskは現在のユーザーのInteractiveToken・LeastPrivilegeで登録し、管理者権限やパスワード登録は要求しません。

**そのユーザーがログオンしている間だけ実行されます。** ログオフ中の実行は対応範囲外です。PCが停止・スリープ中の定刻実行も保証しません。

Task actionは共通`app.bat run <job>`、working directoryはRepository rootです。OAuthは通常ユーザーのCredential Managerに保存したtokenとrefreshだけを使います。ブラウザOAuth・DCR・`mcp auth`の自動起動はしません。認証が必要ならexit 3で停止します。ユーザーが手動で`app.bat mcp auth`を実行してから再実行してください。

## timezone

Phase 8のScheduler登録はdailyの`Asia/Tokyo`だけをサポートします。StartBoundaryへ`+09:00`を明示し、Windowsローカルtimezoneへ読み替えません。任意IANA timezoneやDST地域は、Schema上有効でも`SCHEDULE_TIMEZONE_UNSUPPORTED`で登録を拒否します。手動runにはこのScheduler制限を適用しません。

IANAとWindowsのtimezone名を推測で変換しません。日本のtimezone規則が変更された場合は実装を見直します。[Microsoft StartBoundary](https://learn.microsoft.com/en-us/windows/win32/taskschd/trigger-startboundary)、[登録とlogon type](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskfolder-registertaskdefinition)を参照してください。

weekly/monthly/cron、macOS/Linux Scheduler、常駐daemonは実装していません。

## us_sector_morningサンプルとcoverage制約

`jobs/us_sector_morning.json`はenabled=false、builtin=us_sector_daily、daily 07:00 / Asia/Tokyo、save=true、watchlistSync=falseです。07:00 JSTは米国regular session終了後の運用例であり、休日・早期終了calendarを導入するものではありません。snapshotを改変せず、retrievedAtとsessionAssumptionを記録します。

2026-10-18の再検証でもProviderは条件なしのamerica/stock取得を拒否しました。上限1000件とpagination不在も同じで、全Universe取得手段は未確認です。S&P 500限定取得の成功は全米株coverageの根拠になりません。**schedule applyでのbuiltin登録対応は実装済みですが、同梱Jobはデフォルト無効のため自動登録されません。本番の全米株集計・保存成功は未達です。検証専用S&P 500の503銘柄・20分類では集計・保存成功を実測しました。** 今回のsmokeでは実Task登録・削除を行っていません。

将来の成功応答でも、全件coverage検証を通過するまで保存しません。coverage不足は`US_SECTOR_COVERAGE_INCOMPLETE` / exit1、Provider業務失敗もexit1です。save=falseなら取得・集計のみ行い、metadata.saved=false / resultPath=nullを返します。集計・欠損・重複・rank契約は[Results](RESULTS.md)を参照してください。


過去の実機確認は[SCHEDULER_VERIFICATION_2026-09-27.md](../archive/SCHEDULER_VERIFICATION_2026-09-27.md)に保持しています。
