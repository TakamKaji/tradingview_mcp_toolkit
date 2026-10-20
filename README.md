# TradingView MCP Support

TradingView公式MCPで銘柄をスクリーニングし、結果をPCへ保存して履歴・前回との差分を確認するツールです。WindowsではPythonを自分でインストールせずに使えます。

本プロジェクトは非公式の第三者ツールです。TradingView社の公式製品ではなく、提携・承認を示すものではありません。

条件はJSONファイルで管理します。必要に応じて、結果のWatchlist同期やWindowsでの定期実行も設定できます。

## 必要なもの

- Windows 64-bit（amd64）、PowerShell、インターネット接続
- TradingViewのEssential以上の対象有料プラン（試用プランは対象外。[公式の利用条件](https://www.tradingview.com/mcp/docs)を優先してください）
- 現在PrivateのGitHubリポジトリへのアクセス権

管理者権限やシステムPythonは不要です。現在のバージョンは`0.1.0b1`で、**GitHub Release・tagは未公開**です。

## ダウンロードから接続まで

1. アクセス権のあるGitHubアカウントで[リポジトリ](https://github.com/TakamKaji/tradingview_mcp_support)を開きます。
2. ブランチが`main`であることを確認し、**Code → Download ZIP**から取得します。
3. ZIPを右クリックして「すべて展開」し、`setup.bat`のあるフォルダを開きます。ZIP内から直接実行しないでください。
4. **`setup.bat`を通常のダブルクリックで実行**します。Pythonと必要なライブラリの導入が進みます。
5. 初回は既定ブラウザでTradingViewへログインし、アクセスを許可します。認証済みならブラウザ認可は省略されます。
6. セットアップ画面にログイン・接続確認の成功と「セットアップ完了」が表示されたら導入完了です。

セットアップはMCP接続・Tool一覧を確認します。Screening、Watchlistの更新、定期実行の登録は自動では行いません。失敗したときは[導入手順](docs/user/WINDOWS_SETUP.md)と[トラブル対応](docs/user/TROUBLESHOOTING.md)を参照してください。

## 最初のRead-only操作

展開フォルダをエクスプローラーで開き、アドレス欄に`cmd`と入力してEnterを押します。開いたコマンドプロンプトで次を実行します。

```bat
app.bat run public_sample_screen_daily
app.bat results latest sample_standard_screen
app.bat results history sample_standard_screen --limit 10
```

TradingViewから読み取り、結果JSONをPC内の`results/`へ保存します。**Watchlistへ書き込まず、Schedulerにも登録しません。** Job名と保存結果のScreening名は異なります。前回との差分は[結果マニュアル](docs/user/RESULTS.md)で確認できます。

`sample_screen_daily`はWatchlistを書き換える別のサンプルです。同期や定期登録を使う場合は、先に下の専用マニュアルを確認してください。

## 主な制約

- TradingView公式MCPはBetaで、仕様・取得可能範囲が変わる可能性があります。上位N件の取得を全件取得とは扱いません。
- **全米株全体のセクター集計は未対応**です。条件なしの`america/stock`要求は公式Providerが拒否するため、`us_sector_morning`は`enabled=false`です。S&P 500限定503件の過去の検証成功は全米株成功ではありません。
- SchedulerはWindowsでログオン中のユーザー・毎日・Asia/Tokyoのみ対応します。
- 独立した新規Windowsユーザーでの初回OAuthは未検証です。既存ユーザーの保存済み認証による確認と区別しています。
- 自動売買・発注は行いません。データや指標の完全性、投資成果は保証しません。

## マニュアル

| やりたいこと | 読む文書 |
| --- | --- |
| インストール・初回認証・更新 | [Windows導入](docs/user/WINDOWS_SETUP.md) |
| 条件を選んで実行 | [Screening](docs/user/SCREENING_MANUAL.md) |
| 保存結果・履歴・差分を見る | [Results](docs/user/RESULTS.md) |
| Watchlistと同期する（Write） | [Watchlist](docs/user/WATCHLIST_SYNC.md) |
| Job・定期実行を管理する | [Scheduler](docs/user/SCHEDULE_MANUAL.md) |
| AIにCLI操作を依頼する | [AI利用](docs/user/AI_USAGE.md) |
| エラーを解決する | [トラブル対応](docs/user/TROUBLESHOOTING.md) |

[文書一覧](docs/README.md)から、[開発仕様・API契約](docs/development/README.md)、[過去の検証記録](docs/archive/README.md)、[未公開リリースノート案](docs/release/README.md)にも進めます。

## ライセンス

[MIT License](LICENSE)

第三者の資料・ライブラリには、それぞれの権利・利用条件が適用されます。
