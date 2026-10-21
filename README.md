# TradingView MCP Support

TradingView公式MCPを使い、自分で定義した条件のスクリーニングと結果管理を行う**非公式の補助ツール**です。TradingView社との提携・承認はありません。

## 主な機能

- 公式MCPへの接続・OAuth認証
- JSONで定義したスクリーニングの実行
- 結果の保存・履歴参照・前回比較
- 管理Watchlistへの差分同期（銘柄の追加・削除）
- Jobの手動実行、Windows Task Schedulerによる日次実行

同梱の条件・日次Jobは設定サンプルです。市場・条件・取得列・実行時刻は利用者が設定します。

公式35 ToolのPythonラッパーもありますが、CLIの操作範囲とは異なります。OHLCV・ニュース・財務等の専用CLIや定期取得Jobは未実装です（[機能の対応範囲](docs/user/FEATURES.md)）。

## 必要な環境

| 起動方法 | 必要なもの |
| --- | --- |
| Windowsネイティブ | Windows 64-bit、PowerShell |
| Dockerコンテナ | Windows・macOS等のDocker実行環境とDocker Compose（例：Docker Desktop） |

ホストへのPythonインストールは不要です。インターネット接続と、TradingView公式MCPを利用できるプランが必要です（[公式の利用条件](https://www.tradingview.com/mcp/docs)）。

## インストール・起動

[GitHub Releases](https://github.com/TakamKaji/tradingview_mcp_support/releases)の**Source code (zip)**、またはリポジトリの**main → Code → Download ZIP**を取得し、展開します。

### Windowsネイティブ

`setup.bat`をダブルクリックし、ブラウザでTradingViewへの連携を許可します。接続確認後は、展開フォルダのコマンドプロンプトから`app.bat`を使います（[導入・認証手順](docs/user/WINDOWS_SETUP.md)）。

### Dockerコンテナ

Docker Desktop等を起動し、展開フォルダで実行します。`Dockerfile.mac`と`compose.mac.yml`を使いますが、Mac専用の構成ではありません。

```sh
docker compose -f compose.mac.yml build app
docker compose -f compose.mac.yml run --rm app --version
docker compose -f compose.mac.yml run --rm app jobs list
```

初回OAuthと取得操作は[Dockerマニュアル](docs/user/MAC_DOCKER.md)へ。`mac.command`はmacOS向けの補助起動ファイルです。初回起動でJobや定期登録は自動実行しません。

## 基本的な使い方

認証後、Windowsでは次のRead-onlyサンプルで取得・保存結果を確認できます。

```bat
app.bat screen public_japan_value
app.bat results latest public_japan_value
```

`screen`単体はWatchlistを更新しません。Dockerでの[同じ操作](docs/user/MAC_DOCKER.md#screening手動job結果)も共通CLIを使います。Windowsネイティブの結果は展開先の`results/`、Dockerの結果・認証情報は専用volumeに保存されます。

## 自分の条件を作る

`screenings/public_japan_value.json`を同じフォルダの`my_japan_value.json`へコピーし、`name`も`my_japan_value`にします。条件・取得列・上限などを編集します（[全文JSONと実行手順](docs/user/SCREENING_MANUAL.md#自分の条件を追加する)）。

## Job・定期実行

`jobs/`のサンプルを別名でコピーし、`task.definition`に自分のScreening名を指定します。最初は`enabled=false`・`watchlistSync=false`で手動確認します（[Jobの作り方](docs/user/SCHEDULE_MANUAL.md#自分のjobを作る)）。

Jobは`run Job名`、結果参照は`results latest Screening名`を使います。Dockerでは手動実行まで、定期登録はWindowsネイティブのみです。

## マニュアル

- [Windows導入](docs/user/WINDOWS_SETUP.md) / [Docker導入・OAuth・保存先](docs/user/MAC_DOCKER.md)
- [Screening](docs/user/SCREENING_MANUAL.md) / [結果・履歴・比較](docs/user/RESULTS.md)
- [Watchlist同期](docs/user/WATCHLIST_SYNC.md) / [Job・Scheduler](docs/user/SCHEDULE_MANUAL.md)
- [AIからのCLI利用](docs/user/AI_USAGE.md) / [トラブル対応](docs/user/TROUBLESHOOTING.md)

## 制約・注意事項

- **条件なしの全米株取得は公式MCP Providerが拒否するため未対応**です。最大取得数は1,000行で、上位N件を全件とは扱いません。`us_sector_morning`は無効です（[取得制約](docs/user/SCREENING_MANUAL.md#公式mcp-beta版のスクリーニング制限2026-10-18実機確認)）。
- **`schedule apply`は有効な全Jobを登録・更新します。** 同梱の`sample_screen_daily`は有効かつWatchlist Writeありなので、不要なら登録前に無効化してください。
- DockerはWindows上のDocker Desktop・Linux/amd64でOAuth、Screening、Job、認証・結果の永続化を確認しています。**Mac実機・arm64は未検証**です。[認証volumeの保護と限界](docs/user/MAC_DOCKER.md#データと認証情報の保存場所)も確認してください。

## ライセンス

[MIT License](LICENSE)。第三者の資料・ライブラリには各利用条件が適用されます。
