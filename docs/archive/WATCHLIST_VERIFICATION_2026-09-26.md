# WATCHLIST_VERIFICATION_2026-09-26

> 過去の実測記録です。今回の文書再編で再試験した結果ではありません。[記録索引](README.md)へ戻る。

## 実機検証の範囲

実response調査では、新規専用テストWatchlistへTSE:7203を1回追加し、取得確認、1回削除、空状態取得確認を行いました。そのテストIDだけをcleanup削除し、削除後の取得不能応答も調べました。ユーザー既存Watchlistは変更していません。実ID・テスト名・Provider全文をfixtureへ保存していません。

Unit Test後には別の新規専用テストWatchlistで、同期Python APIの一連の動作も確認しました。

| 確認 | 結果 |
| --- | --- |
| Windows Embedded Python / 権限 | 3.12.8 / 管理者権限なし |
| Phase 6 Engineから取得 | 実Screening結果1件 |
| 初回同期 | success、created=true、1件add、保存mappingと返却ID一致 |
| 同じ入力で再同期 | success、Write 0回、unchangedCount=1 |
| 制御した正常空Envelope入力 | success、1件remove、getで空状態確認 |
| Write policy | create/add/remove/cleanup deleteすべてretry=False、cacheなし |
| 通常syncの禁止Tool | delete/get_active/list/update呼出しなし |
| cleanup | この実行で作成したIDだけをdelete、deleted=trueとID一致を確認 |

空入力は削除経路の確認用に、取得した正常EnvelopeのresultsとreturnedCountを空へ変更したものです。Providerがその時点で0件を返したという意味ではありません。実partial、Write timeout/429、macOS実機は未確認で、失敗時処理はオフラインUnit Testで検証しています。

通常APIにWatchlist削除機能はありません。Phase 8のJob Runnerはこの同期APIを再利用します。[Schedule Manual](../user/SCHEDULE_MANUAL.md)を参照してください。
