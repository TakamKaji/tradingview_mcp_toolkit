# 利用者マニュアル

共通機能を確認し、自分の条件・Jobを作って使うための手順です。同梱の条件や時刻は使用例で、製品が提供する固定の監視条件ではありません。

| 順序・目的 | マニュアル |
| --- | --- |
| できること・Python APIとCLIの違い | [共通機能・サンプル・公式Toolの範囲](FEATURES.md) |
| 1. ダウンロードしてTradingViewへ接続 | [Windowsネイティブ導入](WINDOWS_SETUP.md) / [Docker導入](DOCKER.md) |
| 2. 自分の条件を作り、取得・保存する | [Screeningの作成手順と全文JSON](SCREENING_MANUAL.md#自分の条件を追加する) |
| 3. 保存結果・履歴・前回差分を確認 | [Results](RESULTS.md) |
| 任意：Watchlistを書き換える | [Watchlist](WATCHLIST_SYNC.md) |
| 任意：自分のJob・Windowsの定期実行 | [Jobの作成手順と全文JSON](SCHEDULE_MANUAL.md#自分のjobを作る) |
| AIと会話してJSONを作成 | [ChatGPT・Codex用JSON作成ガイド](AI_JSON_GUIDE.md) |
| AIに操作を頼む | [AIからのCLI利用](AI_USAGE.md) |
| 失敗したとき | [トラブル対応](TROUBLESHOOTING.md) |

コマンドは展開フォルダのコマンドプロンプトで実行します。エクスプローラーのアドレス欄に`cmd`と入力すると、そのフォルダで開けます。PowerShellを使う場合は`app.bat`を`.\app.bat`に読み替えてください。

Dockerでは`docker compose -f compose.docker.yml run --rm app`へCLI引数を渡します。macOSでは補助ファイル`./mac.command`も使えます。定期登録はWindowsネイティブ専用です。

作成した定義は`screen my_japan_value`、Jobは`run my_japan_value_daily`で実行し、結果参照にはScreening名を使います。全文例のファイルを保存してから実行してください。

同梱例を先に試す場合は`public_japan_value`のScreeningや`public_sample_screen_daily`のJobがRead-only＋結果保存です（Windowsネイティブは展開先results、Dockerはvolume）。`sample_screen_daily`のWatchlist同期や`schedule apply/remove`は副作用を伴う任意操作なので、利用者が内容を理解して依頼・実行する場合に限ります。

[文書一覧](../README.md) / [トップREADME](../../README.md)
