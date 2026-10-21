# SCHEDULER_VERIFICATION_2026-09-27

> 過去の実測記録です。今回の文書再編で再試験した結果ではありません。[記録索引](README.md)へ戻る。

## 実機確認（2026-09-26〜27）

通常Windowsユーザー（管理者ではない）・Embedded Python 3.12.8・Tokyo Standard Timeで確認しました。

| 確認 | 結果 |
| --- | --- |
| app.bat jobs list | 正常JSON、exit 0 |
| run sample_screen_daily | 50件保存、新規管理Watchlistへ同期、exit 0 |
| schedule apply/list | sampleと専用Taskを作成・列挙 |
| 空白入りRepository root | 共通app.bat/既存runtimeを使用しTask起動成功 |
| 作成・同設定・時刻変更 | created → updated → updated |
| 時刻と権限 | +09:00と次回時刻が一致、InteractiveToken=3、RunLevel=0 |
| Task Schedulerの手動Run | 結果1件保存、LastTaskResult=0 |
| 日次時刻トリガー | 2026-09-27 06:30:00に実行、結果1件保存、LastTaskResult=0 |
| 同一Job lock保持中 | CLIはalready_running/exit 0、実Taskもexit 0で追加結果なし |
| unsupported timezone | America/New_Yorkを拒否、既存Task設定変更なし |
| disabled / JSON削除 | applyでTaskは残る |
| caseだけ異なるremove名 | 衝突エラー、既存Taskは残る |
| 明示remove / 不存在remove | removed=true / false、いずれもexit 0 |
| cleanup | 今回作成したTask 2件を削除、最終管理Task一覧は空 |

既存ユーザーTaskは変更していません。sample実行で作成した管理Watchlistと`.local/managed_watchlists.json`は保持しています。専用Scheduler JobはWatchlist同期を無効にしました。

ログオフ中の実行、DST地域、別Windows timezoneの実機は未確認で、ログオフ/DSTは対応範囲外です。実Providerでの認証失効・partial・通信失敗を意図的には発生させておらず、エラー契約はUnit Testで確認しています。
