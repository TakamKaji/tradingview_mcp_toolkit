# ドキュメント

初めて利用する方は、[Windows導入](user/WINDOWS_SETUP.md) → [Screening](user/SCREENING_MANUAL.md) → [結果・履歴・比較](user/RESULTS.md)の順に進んでください。[トップREADME](../README.md)にも最短手順があります。

## 操作マニュアル

| 目的 | 文書 |
| --- | --- |
| ダウンロード、セットアップ、TradingView認証、更新 | [Windows導入](user/WINDOWS_SETUP.md) |
| 名前付き条件とRead-onlyサンプルの実行 | [Screening](user/SCREENING_MANUAL.md) |
| 保存先、最新結果、履歴、前回差分の意味 | [Results](user/RESULTS.md) |
| 管理Watchlistへの追加・削除を伴う同期 | [Watchlist](user/WATCHLIST_SYNC.md) |
| Jobの手動実行、Task登録・削除 | [Scheduler](user/SCHEDULE_MANUAL.md) |
| AIへの依頼例と結果の読み方 | [AI利用](user/AI_USAGE.md) |
| 認証・通信・保存・比較のエラー | [トラブル対応](user/TROUBLESHOOTING.md) |

Read-onlyの初回サンプルは`public_sample_screen_daily`です。`sample_screen_daily`はWatchlist Write、`schedule apply/remove`はWindows Taskの作成・更新／削除を伴います。操作の依頼・実行前に各マニュアルを確認してください。

## 開発・調査・リリース情報

- [開発索引](development/README.md)：設計仕様、型付きAPI、保存JSON、Job契約、Windows内部構造、開発・テスト方法
- [過去の記録](archive/README.md)：時点付きの実機検証、旧README、RC Gate、別PC受入手順
- [リリース情報](release/README.md)：`v0.1.0b1`は未公開のリリースノート案

文書の移動対応表とGoogle Drive正本の扱いは[開発索引](development/README.md#文書の移動対応表issue-30)にあります。旧`docs/*.md`は移動案内です。操作マニュアルの本文は`user/`、内部契約は`development/`で管理します。
