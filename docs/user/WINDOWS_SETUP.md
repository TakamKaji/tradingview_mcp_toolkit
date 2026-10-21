# Windowsへの導入とTradingView認証

## 準備するもの

- Windows 64-bit（amd64）、PowerShell、インターネット接続
- TradingView Essential以上の対象有料プラン。試用プランは対象外です（[公式案内](https://www.tradingview.com/mcp/docs)、2026-10-19確認）

システムPython、管理者権限、環境変数の恒久変更は不要です。セットアップはPythonとライブラリをダウンロードするため、完全オフラインでは導入できません。

## ダウンロードする

1. [GitHub Releases](https://github.com/TakamKaji/tradingview_mcp_support/releases)で対象バージョンの**Assets → Source code (zip)**を取得します。Releaseがない場合は`main`ブランチの**Code → Download ZIP**を利用します。
2. ZIPを「すべて展開」し、`setup.bat`と`app.bat`のあるフォルダを開きます。ZIP内から直接BATを実行しないでください。

Gitでmainをcloneしても利用できますが、導入にGitや開発ツールは必要ありません。

## セットアップする

1. **`setup.bat`を普通にダブルクリック**します。「管理者として実行」は不要です。
2. 日本語の案内に従い、Python 3.12.8と実行用ライブラリの準備を待ちます。
3. 未認証の場合だけ既定ブラウザが開きます。TradingViewへログインして、公式のアクセス許可画面で認可します。
4. セットアップ画面がMCP接続とTool一覧を自動で確認します。「ログインと接続確認に成功しました」「セットアップ完了」を確認します。

認証済みなら保存済み認証を再利用し、ブラウザでの再認可は省略します。接続確認に失敗した場合はエラーで停止します。「Python導入が済んだ」だけで接続成功とは判断しないでください。

セットアップはScreening、Watchlist/Alert Write、Task Scheduler登録を自動実行しません。認証情報は通常のWindowsユーザーのCredential Managerに保存します。プロジェクト内の平文tokenファイルへ保存する方式ではありません。

## 安全な初回操作

展開フォルダでエクスプローラーのアドレス欄に`cmd`と入力してEnterを押し、次を実行します。PowerShellでは先頭を`.\app.bat`に変更してください。

```bat
app.bat run public_sample_screen_daily
app.bat results latest sample_standard_screen
```

TradingViewから読み取り、PCの`results/`へJSONを保存します。WatchlistへのWriteや定期実行登録は行いません。詳しくは[Screening](SCREENING_MANUAL.md)と[結果を見る](RESULTS.md)へ進んでください。

## 再実行・認証の確認

通常は`setup.bat`をもう一度ダブルクリックすれば、既存runtimeを再利用し、依存を更新して接続まで確認します。不完全なruntimeはそのruntimeだけを再構築します。アプリを終了してから実行してください。認証情報・保存結果・Watchlist mappingの削除は必要ありません。

手動で接続状況を調べる場合は、展開フォルダで次を実行します。

```bat
app.bat mcp status
app.bat mcp tools
```

`mcp status`だけではブラウザを開きません。`AUTH_REQUIRED`（exit 3）が出たら、`setup.bat`を再実行するか、明示的に`app.bat mcp auth`でブラウザ認可を行います。通信障害を認証情報の一括削除で直そうとしないでください。

自動検証用の`setup.bat --no-pause`と`--skip-auth`はブラウザ認証・MCP接続確認を省略します。通常利用は引数なしのダブルクリックです。`--no-pause`は最後の待機も省略し、`--skip-auth`は最後に待機します。

## 更新・利用終了

更新する場合は新しいソースを別フォルダへ展開してセットアップします。既存の`screenings/`、`jobs/`、`results/`、`.local/managed_watchlists.json`などは必要に応じてバックアップし、旧環境を削除せずに新しい設定を確認してください。旧フォルダを参照するTaskやmappingは自動移行されません。

フォルダを削除しても、登録済みScheduler TaskやCredential Managerの情報は消えません。定期実行を使っていた場合は[Schedulerの削除手順](SCHEDULE_MANUAL.md#定期実行を止める削除操作)を確認し、認証の解除はTradingView側の正規の連携管理から判断してください。tokenをファイルへ書き出して移行しないでください。

## 通信先と未確認事項

導入時は`www.python.org`、`bootstrap.pypa.io`、標準PyPIの場合は`pypi.org`・`files.pythonhosted.org`へHTTPS接続します。独自indexを設定している場合はその配布先も必要です。利用時は`mcp.tradingview.com`、ブラウザ認証は`www.tradingview.com`など公式の認証先を使います。初回OAuth時だけPC内の`127.0.0.1:8765`で認可の戻りを受信します。

独立した新規Windowsユーザーでの初回OAuthは未検証です。保存済み認証での接続成功とは区別しています。過去の実測と個人利用の判断は[記録索引](https://github.com/TakamKaji/tradingview_mcp_support/blob/develop/docs/archive/README.md)に保持しています。

[トラブル対応](TROUBLESHOOTING.md) / [利用者マニュアル一覧](README.md)
