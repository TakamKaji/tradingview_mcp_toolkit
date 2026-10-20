# TradingView MCP Support

TradingView公式MCPを利用して銘柄をスクリーニングし、結果をPCに保存して履歴・前回との差分を確認できる**非公式ツール**です。TradingView社の公式製品ではなく、提携・承認を受けたものではありません。

## このツールでできること

- TradingView公式MCPへの接続・認証と、利用可能Toolの確認
- JSONで定義した自分のスクリーニング条件の実行
- 結果の保存、最新結果・履歴の取得、同じ条件の前回結果との比較
- 設定した管理Watchlistへの差分同期（銘柄の追加・削除を伴います）
- JSONで定義したJobの手動実行と、Windows Task Schedulerへの日次登録

条件・取得列・件数・実行時刻は利用者が設定します。同梱の日本株・S&P 500条件や日次Jobは使用例です。特定条件・時刻の監視サービスを提供するものではありません。

公式MCPにはローソク足・ニュース・財務などのToolもあり、本ツールに型付きPythonラッパーがあります。ただし、それらの専用CLIや定期取得Jobは未実装です。[共通機能・サンプル・Python APIの対応範囲](docs/user/FEATURES.md)で区別しています。

## 必要な環境

- Windows 64-bit、PowerShell、インターネット接続
- TradingView公式MCPを利用できるプラン（[公式の利用条件](https://www.tradingview.com/mcp/docs)を確認）

システムPythonの事前インストールや管理者権限は不要です。

## ダウンロード・セットアップ

1. [GitHub Releases](https://github.com/TakamKaji/tradingview_mcp_support/releases)で利用するバージョンの**Assets → Source code (zip)**を取得します。Releaseがない場合は、`main`ブランチの**Code → Download ZIP**から取得します。
2. ZIPを「すべて展開」し、展開先の`setup.bat`をダブルクリックします。ZIP内から直接実行しないでください。
3. 初回はブラウザでTradingViewにログインし、連携を許可します。認証済みの場合は保存済みの認証を再利用します。
4. セットアップ画面で接続確認成功と「セットアップ完了」を確認します。

## 基本的な使い方

展開フォルダをエクスプローラーで開き、アドレス欄に`cmd`と入力してEnterを押します。

```bat
app.bat screen public_japan_value
app.bat results latest public_japan_value
app.bat results history public_japan_value --limit 10
```

これは共通の`screen`コマンドに同梱条件`public_japan_value`を指定する例です。TradingViewから読み取り、PCへJSONを保存します。`screen`単体はWatchlist同期や定期登録を行いません。保存済み結果は同じScreening名で参照します。

## 自分のスクリーニング条件を作る

`screenings/public_japan_value.json`を`screenings/my_japan_value.json`へコピーし、内部の`name`も`my_japan_value`へ変更します。条件・取得列・上限などを編集して、`app.bat screen my_japan_value`で実行できます。

[Screeningマニュアル](docs/user/SCREENING_MANUAL.md#自分の条件を追加する)に、コピー・編集・全文JSON・実行・エラー対処をまとめています。作成した条件をJobにする手順は[Job・Schedulerマニュアル](docs/user/SCHEDULE_MANUAL.md#自分のjobを作る)へ進んでください。

## 同梱サンプルの利用

日本株割安、S&P 500、公式presetなどの[Screening例](docs/user/SCREENING_MANUAL.md#同梱サンプルからコピー元を選ぶ)と、それを呼ぶ[Job例](docs/user/SCHEDULE_MANUAL.md#同梱jobは使用例)を同梱しています。自由にコピーして別名で使えます。

Jobの初回試用は`app.bat run public_sample_screen_daily`で、保存結果のScreening名は`sample_standard_screen`です。これはRead-onlyですが、別の`sample_screen_daily`はWatchlist Writeを伴い、初期設定で定期登録対象です。実行・登録前に対象と副作用を確認してください。

## マニュアル

- [機能と利用方法の対応範囲](docs/user/FEATURES.md)
- [Windows導入・認証](docs/user/WINDOWS_SETUP.md)
- [Screening](docs/user/SCREENING_MANUAL.md)
- [結果・履歴・比較](docs/user/RESULTS.md)
- [Watchlist同期（書き込みあり）](docs/user/WATCHLIST_SYNC.md)
- [Scheduler](docs/user/SCHEDULE_MANUAL.md)
- [AIからのCLI利用](docs/user/AI_USAGE.md)
- [トラブル対応](docs/user/TROUBLESHOOTING.md)

開発用のテスト・設計資料は同じリポジトリの`develop`ブランチで管理しています。

## TradingView公式MCP側の取得制限

**全米株の条件なし一括取得は、TradingView公式MCP Providerがリクエストを拒否するため利用できません**（2026年10月18日の実機検証）。公式`run_screener`には最大1,000行の制限があり、全件取得に必要なページング手段も確認できていません。

これは**本ツール独自の取得制限や認証エラーではなく、公式MCP側の応答・取得仕様に起因する制約**です。不完全な銘柄集合を全米株の集計結果として表示しないため、`us_sector_morning`は無効にしています。条件付きの銘柄スクリーニングは利用できます。詳細は[公式MCPの実測制約](docs/user/SCREENING_MANUAL.md#公式mcp-beta版のスクリーニング制限2026-10-18実機確認)をご覧ください。

## ライセンス

[MIT License](LICENSE)。第三者の資料・ライブラリには、それぞれの権利・利用条件が適用されます。
