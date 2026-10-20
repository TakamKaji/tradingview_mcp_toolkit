# JobとWindowsの定期実行

## Jobを確認して手動実行する

```bat
app.bat jobs list
app.bat run public_sample_screen_daily
app.bat schedule list
```

`jobs list`は定義を検証して一覧を返します。`schedule list`は管理対象Taskの列挙だけで、登録・削除を行いません。

| Job | 手動実行の動作 | 初期の定期登録 |
| --- | --- | --- |
| public_sample_screen_daily | TradingView Read＋JSON保存、Watchlist Writeなし | 対象外（enabled=false） |
| sample_screen_daily | 取得・保存＋**管理WatchlistへWrite** | 対象（enabled=true） |
| public_japan_value_dailyなどpublic系4例 | TradingView Read＋JSON保存、Watchlist Writeなし | 対象外（enabled=false） |
| us_sector_morning | 全米株取得がProvider制約で未対応 | 対象外（enabled=falseを維持） |

`enabled=false`は定期登録の対象外という意味です。明示した手動`run`は実行できるため、無効なJob名なら安全と判断しないでください。全米株Jobは初回確認に使いません。

## Jobを追加する

`jobs/`内のread-only公開例をコピーし、ファイル名と内部`name`を同じ新しい名前にします。`task.definition`には実在するScreening名を指定します。主な設定は次のとおりです。

| 設定 | 意味 |
| --- | --- |
| enabled | schedule applyの登録対象にするか |
| output.save | 結果をPC内へ保存するか |
| output.watchlistSync | Watchlist同期を呼ぶか（Screening側の有効設定も必要） |
| schedule.type / time / timezone | 現在の定期登録はdaily・HH:MM・Asia/Tokyoのみ |

最初は`enabled=false`、`watchlistSync=false`で手動確認してください。JobごとのBATを作成・編集する必要はありません。定義の不正や参照ミスがあると一覧・登録は失敗します。

## 定期実行を登録する（作成・更新操作）

**`schedule apply`は有効な全JobのWindows Taskを作成・更新します。特定Jobだけを選ぶコマンドではありません。** 同梱の`sample_screen_daily`は有効なので、そのまま適用するとWatchlist Writeを伴う定期実行が登録されます。

登録したいJobの条件、保存、同期、時刻を確認し、それ以外のJobを無効にしたうえで、利用者が登録を意図する場合だけ次を実行します。AIに依頼する場合も登録対象と副作用の承認を明示してください。

```bat
app.bat schedule apply
app.bat schedule list
```

Task名は`TradingViewMcpSupport__<job名>`です。定義を無効にしたりファイルを消しただけでは、既存Taskは自動削除されません。

## 定期実行を止める（削除操作）

**次は`sample_screen_daily`の管理Taskを削除します。** 利用者が削除を意図する場合だけ実行してください。

```bat
app.bat schedule remove sample_screen_daily
app.bat schedule list
```

指定名と一致するTaskだけが対象です。Job JSONを既に削除していても明示removeは可能です。保存結果やTradingView Watchlist自体はこの操作で削除されません。

## 実行条件と失敗時

- Windowsで、そのTaskを登録したユーザーがログオン中に実行します。管理者・パスワード登録は不要です。PC停止・スリープ中の定刻実行は保証しません。
- 対応する定期登録はdaily / Asia/Tokyoです。他timezone・DST・weekly・monthly・cron・macOS/LinuxのSchedulerは非対応です。
- 保存済み認証を使い、認証切れでもブラウザを自動起動しません。`AUTH_REQUIRED`なら手動で認証し直します。
- 同じJobが実行中なら重複実行は`already_running`でスキップし、終了コード0です。
- 失敗時は`status`、`errors`、保存・同期済みの情報を確認します。一部操作を自動で取り消すことはありません。

[Job・Taskの内部契約](https://github.com/TakamKaji/tradingview_mcp_support/blob/develop/docs/development/JOBS_SCHEDULER.md) / [トラブル対応](TROUBLESHOOTING.md) / [利用者マニュアル一覧](README.md)
