# TradingView MCP Support

TradingView公式MCPを使って銘柄スクリーニング、結果保存、履歴・前回比較を行う**非公式ツール**です。TradingView社との提携・承認関係はありません。

Windows 64-bit・PowerShell・インターネット接続、TradingViewの公式MCP対応プランが必要です。システムPythonや管理者権限の事前準備は不要です。対応プランの最新条件は[公式サイト](https://www.tradingview.com/mcp/docs)をご確認ください。

## 導入

1. mainブランチからソースZIPを取得して、フォルダに**すべて展開**します。
2. 展開した`setup.bat`を通常のダブルクリックで実行します。
3. 初回はブラウザでTradingViewへログインし、アクセス許可します。
4. 画面に接続確認成功・セットアップ完了が表示されたら準備完了です。

専用のGitHub Release配布ZIPは準備中です。**まだGitHub Releaseやtagは公開していません。**

## 安全な初回操作

展開フォルダをエクスプローラーで開き、アドレス欄に`cmd`と入力してEnterを押し、次を実行します。

```bat
app.bat run public_sample_screen_daily
app.bat results latest sample_standard_screen
app.bat results history sample_standard_screen --limit 10
```

この操作はTradingViewからのReadとPC内のJSON保存のみ。WatchlistへのWrite、Scheduler登録はしません。**`sample_screen_daily`はWatchlistへのWriteを伴う別のサンプル**です。

## マニュアル

- [Windows導入と認証](docs/user/WINDOWS_SETUP.md)
- [Screening](docs/user/SCREENING_MANUAL.md)
- [結果・履歴・比較](docs/user/RESULTS.md)
- [Watchlist同期（Write）](docs/user/WATCHLIST_SYNC.md)
- [Scheduler](docs/user/SCHEDULE_MANUAL.md)
- [AIからのCLI利用](docs/user/AI_USAGE.md)
- [トラブル対応](docs/user/TROUBLESHOOTING.md)
- [文書一覧](docs/README.md)

## 制約

- TradingView公式MCPはBeta版です。
- **全米株セクター集計は未対応**。条件なし全米株取得がProviderに拒否されるため`us_sector_morning`は無効です。
- SchedulerはWindows・ログオン中のユーザー・Asia/Tokyo日次のみです。
- 独立新規Windowsユーザーの初回OAuthは未検証です。
- 自動売買・発注は行いません。

開発作業・テスト・内部仕様・過去の検証記録は**同じリポジトリの`develop`ブランチ**で管理します。

## ライセンス

[MIT License](LICENSE)。第三者の資料やライブラリは各権利・利用条件に従います。
