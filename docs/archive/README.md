# 過去の検証・受入・リリース準備記録

このフォルダは**歴史資料**です。各文書の日付・HEAD・実測条件を確認してください。当時の「未実施」「Draft」「未マージ」は、後日の判定で書き換えていません。現在の操作は[利用者マニュアル](../user/README.md)、契約は[開発索引](../development/README.md)から確認します。

| 記録 | 内容・読み方 |
| --- | --- |
| [旧README（2026-10-19再編前）](README_BEFORE_ISSUE_30.md) | Phase別の実装説明、設定・SDK・Governor例、2026-09-25以降の実機・テスト結果を保持 |
| [Watchlist 2026-09-26](WATCHLIST_VERIFICATION_2026-09-26.md) | 当時の専用テストWatchlistでのWrite・確認・cleanup。通常の利用手順ではない |
| [Scheduler 2026-09-26〜27](SCHEDULER_VERIFICATION_2026-09-27.md) | Task登録・起動・削除の当時の実測。現在のTaskを操作する指示ではない |
| [Windows 2026-10-18](WINDOWS_VERIFICATION_2026-10-18.md) | 空runtime導入と保存済みcredentialでの接続。新規ユーザー初回OAuthは未実施 |
| [MCP再検証 2026-10-18](MCP_VERIFICATION_2026-10-18.md) | Discovery、少量Screening、当時のProvider制約。本文は後続の追加試験前の記録 |
| [Results・Phase 9の実測](RESULTS_VERIFICATION.md) | 2026-09-27、10-18の段階的検証と、23時台の本番拒否／S&P 500限定集計 |
| [RC Gate・判定履歴](RELEASE_CANDIDATE.md) | PR #29準備時のA〜E、旧HEADの669 passed / 5 skipped、後日の所有者による通常setupスモークとPrivate利用判断 |
| [別PC受入手順](SECOND_PC_ACCEPTANCE_TEST.md) | 当時のPR #29ブランチを使う試験手順。一般向けのmain導入手順ではない |

## 現在と混同しない事項

- PR #19と#29は再編基点mainへ統合済みです。全米株取得のProvider制約は[Issue #18](https://github.com/TakamKaji/tradingview_mcp_support/issues/18)で継続します。
- 2026-10-18 23時台に全米株Jobを実際に試行し、Provider拒否・exit 1・保存なしを確認しました。検証専用S&P 500では503銘柄・20分類の集計・保存を確認しましたが、全米株成功ではありません。
- 2026-10-19の通常setupの所有者実機スモークは保存済みcredentialを利用しています。独立新規Windowsユーザーの初回OAuthは未実施のままです。個人利用のリスク受容を成功の記録に置き換えません。
- RC文書は途中のNo-Go条件と最終のPrivate利用・main統合GO判断を併記しています。[最新判定](RELEASE_CANDIDATE.md#2026-10-19-最新判定文字化け修正後のwindows実機確認済み)が当時の最終報告です。GitHub Release・tag・Public公開は未承認・未実施です。
- 今回の文書再編では実MCP・OAuth・pytest/ruffの再試験は行いません。各記録は今回のHEADでの試験合格を意味しません。

[文書一覧](../README.md)
