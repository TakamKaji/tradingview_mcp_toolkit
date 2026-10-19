# TradingView MCP Support 0.1.0b1（Windows Beta）— Release Notes案

> **未公開の候補文書**：Issue #28のGo/No-Goと実機検証が完了するまでGitHub Release・tagを発行しません。

## このβ版でできること

- TradingView **公式MCP**（OAuth 2.1）への接続と、利用可能Toolの一覧・差分確認
- TradingViewスクリーニングをJSON定義で実行し、結果を日付別JSONへ非上書き保存
- 日本株・米国株の条件付きScreening／公式preset／symbolset（Providerでの対応範囲内）
- 保存済みScreeningの履歴と同一定義の直近2件比較（条件fingerprint一致時のみ）
- 登録済みアプリ管理Watchlistの差分同期（**設定による明示Write**）
- 共通Job Runner、Windows Task Scheduler（Asia/Tokyo daily。Windowsログオン中のみ）
- システムPython不要のWindows Embedded Python 3.12.8 `setup.bat` 導入
- 全米株セクター集計の内部計算・保存・Job統合コード（ただし次項の制限により本番全米株Jobは既定無効）

## TradingView公式MCP Betaの現時点の制約

2026-10-18、TradingView公式MCP server 1.30.0で確認した制約です。**条件を全省略した`america/stock`Screener要求は公式Provider側で拒否**されます。Toolの`limit`は最大1000行、当時のschemaにはoffset/page/cursorがなく、全米株を完全取得する方式を確認できていません。

そのため全米株全体のセクター平均は**提供しません**。失敗する自動Taskを避けるため`us_sector_morning`は`enabled=false`です。一方、検証用のS&P 500フィルターでは503銘柄の全件取得・20セクター集計・保存に成功しました。これは全米株全体の成功ではありません。

この制約は**検証時点のβ版の挙動**であり、TradingViewが将来も永久に対応しないという意味ではありません。最新状況は[Screening Manual](SCREENING_MANUAL.md)と[Issue #18](https://github.com/TakamKaji/tradingview_mcp_support/issues/18)を参照してください。

## 導入と利用環境

Windows 64-bit、PowerShell・インターネット接続が必要です。セットアップ時にPython.orgやパッケージ配布先へ接続します。TradingView公式MCPには対象プランが必要です。システムPythonの事前導入は不要です。

```bat
setup.bat
app.bat mcp status
app.bat mcp auth
app.bat mcp tools
app.bat run public_sample_screen_daily
```

`public_sample_screen_daily`はread-onlyでWatchlist Writeや自動Scheduler登録を行いません。`sample_screen_daily`はWatchlist同期するサンプルなので、初回確認には使わないでください。開発者向けpytest/ruffは通常セットアップに含まれず、`requirements-dev.txt`から明示導入します。

詳細は[Windows Setup](WINDOWS_SETUP.md)をご覧ください。

## 注意・未検証

- このβ版は投資助言、価格や指標の正確性・完全性を保証しません。
- TradingView Providerの仕様・Tool数・銘柄カバレッジは変更され得ます。条件が黙って無視された応答、件数不整合、全件取得できていない応答を安全側で区別します。
- 新規Windowsアカウントでの初回OAuthは未実施です。保存済みcredentialの成功で代替せず、必須Gateが揃うまで公開はNO-GOです。統合後の回帰・クリーンsetup・仕様同期・配布点検の実測は[Release Candidate Gate](RELEASE_CANDIDATE.md)で管理します。
- macOSからの通常Python CLIの想定はありますが、このWindows β版のリリース検証範囲には含めません。
