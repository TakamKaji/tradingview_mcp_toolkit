# 利用者マニュアル

| 順序・目的 | マニュアル |
| --- | --- |
| 1. ダウンロードしてTradingViewへ接続 | [Windows導入](WINDOWS_SETUP.md) |
| 2. 銘柄を取得して保存 | [Screening](SCREENING_MANUAL.md) |
| 3. 保存結果・履歴・前回差分を確認 | [Results](RESULTS.md) |
| 任意：Watchlistを書き換える | [Watchlist](WATCHLIST_SYNC.md) |
| 任意：Job・Windowsの定期実行 | [Scheduler](SCHEDULE_MANUAL.md) |
| AIに操作を頼む | [AIからのCLI利用](AI_USAGE.md) |
| 失敗したとき | [トラブル対応](TROUBLESHOOTING.md) |

コマンドは展開フォルダのコマンドプロンプトで実行します。エクスプローラーのアドレス欄に`cmd`と入力すると、そのフォルダで開けます。PowerShellを使う場合は`app.bat`を`.\app.bat`に読み替えてください。

最初は`public_sample_screen_daily`を使います。これはTradingView Readのみ＋PC内のJSON保存です。`sample_screen_daily`のWatchlist同期や`schedule apply/remove`は副作用を伴う任意操作なので、利用者が内容を理解して依頼・実行する場合に限ります。

[文書一覧](../README.md) / [トップREADME](../../README.md)
