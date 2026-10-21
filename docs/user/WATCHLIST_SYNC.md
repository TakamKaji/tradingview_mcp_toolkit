# 管理Watchlistと同期する（Write）

**Watchlist同期はTradingView上の銘柄を追加・削除します。** 初回の動作確認には不要です。Read-onlyの`public_sample_screen_daily`や`screen`は同期を行いません。

## 実行前に確認する

1. [Job一覧](../../jobs/)と対象JSONで、参照するScreeningと`output.watchlistSync`を確認します。
2. Screeningの`watchlist.enabled`と`watchlist.name`、抽出条件・上限を確認します。
3. 必要なら`app.bat screen sample_standard_screen`で先に結果を確認します。この操作は取得・ローカル保存だけです。
4. 自分のWatchlistへの追加・削除を伴う操作として、対象Jobの実行を判断します。AIに任せる場合も、どのJobの同期を許可するか明示してください。

同梱の`sample_screen_daily`は、`sample_standard_screen`を実行し、結果を保存してWatchlistへ同期する運用サンプルです。次は**実Writeを伴う任意操作**です。

```bat
app.bat run sample_screen_daily
```

Jobで同期を有効にし、Screening側でもWatchlistが有効な場合に同期します。結果JSONの`watchlistSync`、`status`、`errors`を確認してください。終了コード0でも部分成功の場合があり、全操作完了を保証しません。

## どのWatchlistが変わるか

アプリが作成して`.local/managed_watchlists.json`へ記録したIDだけが管理対象です。名前が同じ既存Watchlistを勝手に採用しません。初回は新規作成するため、同名のWatchlistがあっても別に作られます。mappingを既存のIDへ手で置き換えないでください。

以後は取得結果との差分だけを追加・削除します。**正常な0件結果は管理Watchlistを空にします。** 上位N件の結果なら、そのN件との同期であり、条件に該当する全銘柄の同期ではありません。並び順だけの違いでWriteは行いません。

通常同期はWatchlist自体の削除、名前変更、アクティブWatchlistの変更を行いません。

## 失敗したとき

失敗・部分結果や不正な銘柄をそのまま空の成功結果として同期しません。ただしWrite途中で失敗すると、一部の追加・削除が既に反映されている場合があります。自動再送・自動rollbackはしないため、返された確定済み操作と実際の状態を確認してください。

mapping保存失敗やアクセス不能の場合、`.local/`やcredentialの一括削除で直そうとせず、元データを残して診断します。mappingを失うと同じ名前から管理対象を復元できず、新規作成につながる場合があります。

[同期の内部契約・Python API](../development/SCREENING_API.md) / [Scheduler](SCHEDULE_MANUAL.md) / [利用者マニュアル一覧](README.md)
