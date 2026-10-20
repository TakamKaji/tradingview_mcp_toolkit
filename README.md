# TradingView MCP Support

TradingView公式MCPを利用して銘柄をスクリーニングし、結果をPCに保存して履歴・前回との差分を確認できる**非公式ツール**です。TradingView社の公式製品ではなく、提携・承認を受けたものではありません。

## 必要な環境

- Windows 64-bit、PowerShell、インターネット接続
- TradingView公式MCPを利用できるプラン（[公式の利用条件](https://www.tradingview.com/mcp/docs)を確認）

システムPythonの事前インストールや管理者権限は不要です。

## ダウンロード・セットアップ

1. [GitHub Releases](https://github.com/TakamKaji/tradingview_mcp_support/releases)で利用するバージョンの**Assets → Source code (zip)**を取得します。Releaseがない場合は、`main`ブランチの**Code → Download ZIP**から取得します。
2. ZIPを「すべて展開」し、展開先の`setup.bat`をダブルクリックします。ZIP内から直接実行しないでください。
3. 初回はブラウザでTradingViewにログインし、連携を許可します。認証済みの場合は保存済みの認証を再利用します。
4. セットアップ画面で接続確認成功と「セットアップ完了」を確認します。

## 最初の実行（Read-only）

展開フォルダをエクスプローラーで開き、アドレス欄に`cmd`と入力してEnterを押します。

```bat
app.bat run public_sample_screen_daily
app.bat results latest sample_standard_screen
app.bat results history sample_standard_screen --limit 10
```

この操作はTradingViewからデータを読み取り、結果をPCに保存するだけです。Watchlistの書き換えやScheduler登録は行いません。別サンプルの`sample_screen_daily`にはWatchlistへの書き込みがあるため、実行前にマニュアルを確認してください。

## TradingView公式MCP側の取得制限

**全米株の条件なし一括取得は、TradingView公式MCP Providerがリクエストを拒否するため利用できません**（2026年10月18日の実機検証）。公式`run_screener`には最大1,000行の制限があり、全件取得に必要なページング手段も確認できていません。

これは**本ツール独自の取得制限や認証エラーではなく、公式MCP側の応答・取得仕様に起因する制約**です。不完全な銘柄集合を全米株の集計結果として表示しないため、`us_sector_morning`は無効にしています。条件付きの銘柄スクリーニングは利用できます。詳細は[公式MCPの実測制約](docs/user/SCREENING_MANUAL.md#公式mcp-beta版のスクリーニング制限2026-10-18実機確認)をご覧ください。

## マニュアル

- [Windows導入・認証](docs/user/WINDOWS_SETUP.md)
- [Screening](docs/user/SCREENING_MANUAL.md)
- [結果・履歴・比較](docs/user/RESULTS.md)
- [Watchlist同期（書き込みあり）](docs/user/WATCHLIST_SYNC.md)
- [Scheduler](docs/user/SCHEDULE_MANUAL.md)
- [AIからのCLI利用](docs/user/AI_USAGE.md)
- [トラブル対応](docs/user/TROUBLESHOOTING.md)

開発用のテスト・設計資料は同じリポジトリの`develop`ブランチで管理しています。

## ライセンス

[MIT License](LICENSE)。第三者の資料・ライブラリには、それぞれの権利・利用条件が適用されます。
