# TradingView MCP Support 0.1.0b1 — 初回Beta Release Notes案

> 編集用注記：**未公開・未承認**。2026-10-31の公開監査はNO-GO。実機検証基点mainは`d5f3536f12c1743562082fc64e1629143a36f8ee`。短い展開先と日本株データ品質の注意書きをmainへ選択反映した後、最終SHAをここに追記する。[発行前チェックリスト](RELEASE_CHECKLIST_0.1.0b1.md)と[Issue #33](https://github.com/TakamKaji/tradingview_mcp_support/issues/33)で承認するまでtag・Releaseを作成しない。以下が一般利用者向け本文案。

TradingView公式MCPを使い、JSONで指定した条件で銘柄を検索し、結果をローカルに保存・比較するCLIツールの初回β版です。**TradingView社の公式製品ではなく、提携・承認を受けていません。**

## できること

- 日本株・米国株等の条件付きScreening、結果JSON保存、履歴・同条件の前回比較
- 保存JSONから日本語/英語のHTML・CSVを作成
- 複数操作のJob実行、明示設定による管理Watchlist同期、Windowsの定期実行
- 公式MCPの35 Tool用Pythonラッパー。専用CLI・Jobや全引数への対応範囲はToolごとに異なります
- AI共通ガイド・Schema・サンプルによる条件作成支援。AI製品ごとの独立受入がすべて完了した版ではありません

## 利用環境と導入

Windows 11 64-bitで新規runtimeの導入、保存済み認証による公式MCP接続・35 Tool取得・Read-only結果保存・HTML/CSV変換を確認しました。Windowsネイティブ版はホストへのPython事前インストールが不要です。

インターネット接続と、**TradingView Essential以上の対象有料プラン**が必要です。試用プランは対象外です。公式MCPはBetaで、認証・対象プラン・呼出制限は変更されるため[公式案内](https://www.tradingview.com/mcp/docs)を確認してください（2026-10-31確認、目安はユーザーあたり毎分約100 Tool呼出）。

1. このReleaseの**Source code (zip)**を取得して、書き込み可能な短いパス・短いフォルダ名で展開します。
2. Windowsでは`setup.bat`をダブルクリックし、公式ブラウザ画面で必要なOAuth認可を行います。
3. 展開フォルダでコマンドプロンプトを開き、Read-onlyサンプルを実行します。

```bat
app.bat run public_sample_screen_daily
app.bat results latest sample_standard_screen
```

結果は展開先の`results/`へ保存されます。このJobはWatchlistへ書き込まず、Scheduler登録もしません。`sample_screen_daily`は同期を含む別のサンプルなので初回確認には使わないでください。詳細は同梱の`docs/user/WINDOWS_SETUP.md`・`RESULTS.md`をご覧ください。

Docker Desktop等とComposeによる利用も可能です。`docker compose -f compose.docker.yml build app`で構築し、認証・Read手順は同梱の`docs/user/DOCKER.md`へ。Windows Docker Desktop / Linux amd64では過去に所有者が初回OAuth・Read・volume永続化を確認しています。認証volumeはOSの暗号化Keychainではありません。

## 既知の制限・未検証環境

- **全件性を確認してください。** 上限付き結果は市場全件ではありません。今回の同梱サンプルも50/1,947件、`completeCoverage=false`でした。返却件数・総件数・条件無視・null・時点を確認し、古いlatestを今回の成功結果と取り違えないでください。
- 全米株の条件なし一括取得はProvider制約があり、`us_sector_morning`は無効です。S&P 500等の限定母集団の成功を全米株の完全取得と扱いません。
- 東証プライム全件の確定・AIによる自然言語の独立受入は継続課題です。母集団の無断代用や、承諾のない外部名簿取得は行いません（[#58](https://github.com/TakamKaji/tradingview_mcp_support/issues/58)）。
- 日本株の複数市場シンボル数は企業数ではありません。NAG等の低流動性銘柄では、古い日足を含む25本平均から大きなSMA25乖離が出る場合があります。取引所・日付・出来高・重複を確認してください。製品コアの計算不具合と確定したものではなく、全生データの独立監査は継続中です（[#70](https://github.com/TakamKaji/tradingview_mcp_support/issues/70)）。
- Providerの取得列・filter・通貨ラベル・OHLCV形式・時刻範囲には観測上の注意点があります。同梱の`PROVIDER_VERIFICATION.md`を確認し、データの正確性・完全性を無条件に保証しません。
- **新規Windowsユーザーでの初回OAuth、Mac実機・arm64は未検証**です。保存済みWindows認証やamd64の確認で代替しません。
- パスが深すぎるとWindowsでpip導入が失敗する場合があります。元ZIPを短い新規フォルダへ展開して再実行してください。

自作コードはMIT Licenseです。TradingViewの資料・データと依存ライブラリには、それぞれの利用条件が適用されます。このツールは投資助言やデータ品質の保証を提供するものではありません。
