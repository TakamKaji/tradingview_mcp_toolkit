# 開発・設計資料

利用手順は[利用者マニュアル](../user/README.md)へ。ここでは設計・API・内部JSONと実装境界を扱います。過去の検証は[archive](../archive/README.md)、リリースノート案は[release](../release/README.md)に分離しています。

## 契約から探す

| 対象 | 参照先 |
| --- | --- |
| 全体設計・要件 | [実装仕様書](tradingview_screening_system_spec.md) |
| 型付き35 Tool API・OAuth・通信制御 | [API案内](API.md)、仕様書の[Client](tradingview_screening_system_spec.md#13-tradingviewclient-設計)・[Schema](tradingview_screening_system_spec.md#14-pydantic-schema設計)・[RequestGovernor](tradingview_screening_system_spec.md#15-requestgovernor)・[OAuth](tradingview_screening_system_spec.md#17-oauth--認証情報)・[全35 Tool](tradingview_screening_system_spec.md#20-tradingview公式mcp-全35-toolラッパー) |
| Screening定義・Providerへの写像 | 仕様書の[定義](tradingview_screening_system_spec.md#9-screening定義)・[selector/件数契約](tradingview_screening_system_spec.md#36-screening-selector件数契約の拡張2026-10-18--issue-22) |
| 保存・fingerprint・履歴・比較 | [Results JSON契約](RESULTS.md)、仕様書の[Phase 11](tradingview_screening_system_spec.md#37-保存screeningの履歴前回差分phase-11--issue-24) |
| WatchlistのPython API | [API例と入力契約](SCREENING_API.md)、[ownership・lock・失敗回復](WATCHLIST_SYNC.md) |
| Job Runner・Scheduler | [Job/Task契約](JOBS_SCHEDULER.md)、[CLI・builtin契約](CLI_CONTRACT.md) |
| Windows bootstrap・isolated mode | [Runtime内部構造](WINDOWS_RUNTIME.md) |
| Dockerコンテナ認証の境界と受入状況 | [Issue #40の実装・検証記録](DOCKER_VALIDATION.md) |
| 開発依存・テスト | [開発・検証手順](DEVELOPMENT.md) |
| develop/mainの共有コミット運用 | [cherry-pick手順](BRANCH_WORKFLOW.md) |
| Public公開前の監査・未解決事項 | [最新再監査（2026-10-31）](PUBLIC_RELEASE_REAUDIT_2026-10-31.md)、[今回の依存ライセンス](PUBLIC_DEPENDENCY_LICENSES_2026-10-31.md)、[旧監査](PUBLIC_RELEASE_AUDIT.md)、[発行前チェックリスト](../release/RELEASE_CHECKLIST_0.1.0b1.md) |
| 公式MCPの根拠資料 | [公式資料への参照先](TRADINGVIEW_MCP_OFFICIAL_REFERENCE.md)、[公式の現行ページ](https://www.tradingview.com/mcp/docs) |
| 全Toolマニュアル・条件カタログの根拠と未確認事項 | [2026-10-26の静的・少量Read検証](MCP_MANUAL_VERIFICATION_2026-10-26.md) |
| 全35 Toolの機能同等性・OHLCV引数拡張 | [2026-10-27の監査・Read検証](MCP_PARITY_AUDIT_2026-10-27.md) |
| AI Screeningの外部利用承諾・実行範囲 | [2026-10-27の文書・4ケース検証](AI_SCREENING_CONSENT_VERIFICATION_2026-10-27.md) |

全米株の取得は未対応です。仕様書[19.3](tradingview_screening_system_spec.md#193-phase-9-coverage契約とprovider制約2026-09-27)のblocking limitationを維持し、[19.5](tradingview_screening_system_spec.md#195-builtin-job保存scheduler)の同梱`us_sector_morning.enabled=false`を変更しません。S&P 500限定503件・20分類の実測は全米株成功の根拠にはなりません。[Issue #18](https://github.com/TakamKaji/tradingview_mcp_support/issues/18)で追跡します。

## Google Drive正本とRepository版

非公開の外部仕様正本は所有者が管理します。公開用Repositoryには文書ID・非公開URLを掲載せず、正本を変更する場合の先行更新・読み戻し確認は所有者の非公開環境で行います。

Issue #30では**Repository内の配置だけを変更**し、仕様本文はバイト単位で保持しました。基点main `9a80046a47e6a784c41db85f8245ccca8163175c`をcheckoutした作業ツリーの移動前後のSHA-256はともに`0f6e028d69fa188f7d9bb752f52bc44f44accbb6a7cc51def5d6811356929778`です（Git内の改行正規化とは区別）。Driveへの更新・新しい同期確認は実施していません。本文内に残る旧配置名やPhase時点の記述を、この再編で仕様変更として書き換えていません。新しい文書配置は次の表を参照してください。

## 文書の移動対応表（Issue #30）

再編基点は上記mainです。旧`docs/*.md`は移動案内を保持し、本文は下記の分類で管理します。仕様19.3〜19.5・36/37節、Results、Watchlist、Screeningの旧見出しリンクにも案内を残します。`scripts/setup-ui.ps1`の旧Windows案内先も残すため、機能コードは変更しません。仕様本文中の配置例は将来の仕様同期時に別途扱います。

| 従来の文書 | 分類 | 現在の本文・保持先 |
| --- | --- | --- |
| README.md | 利用者／開発／検証履歴の混在 | [新README](../../README.md)。旧全文は[歴史資料](../archive/README_BEFORE_ISSUE_30.md) |
| WINDOWS_SETUP.md | 利用者＋内部構造＋検証履歴 | [導入手順](../user/WINDOWS_SETUP.md)、[内部構造](WINDOWS_RUNTIME.md)、[実機記録](../archive/WINDOWS_VERIFICATION_2026-10-18.md) |
| SCREENING_MANUAL.md | 利用者＋同期Python API | [Screening操作](../user/SCREENING_MANUAL.md)、[同期API](SCREENING_API.md) |
| RESULTS.md | 利用者＋JSON契約＋検証履歴 | [操作](../user/RESULTS.md)、[契約](RESULTS.md)、[実測](../archive/RESULTS_VERIFICATION.md) |
| WATCHLIST_SYNC.md | 内部契約＋検証履歴 | [操作](../user/WATCHLIST_SYNC.md)、[契約](WATCHLIST_SYNC.md)、[実測](../archive/WATCHLIST_VERIFICATION_2026-09-26.md) |
| SCHEDULE_MANUAL.md | 利用者＋Job/Task契約＋検証履歴 | [操作](../user/SCHEDULE_MANUAL.md)、[契約](JOBS_SCHEDULER.md)、[実測](../archive/SCHEDULER_VERIFICATION_2026-09-27.md) |
| AI_USAGE.md | 利用者＋CLI/builtin契約 | [AI利用](../user/AI_USAGE.md)、[内部契約](CLI_CONTRACT.md) |
| tradingview_screening_system_spec.md | 開発・設計仕様 | [実装仕様](tradingview_screening_system_spec.md)。本文不変 |
| TRADINGVIEW_MCP_OFFICIAL_REFERENCE.md | 開発・技術参照 | [公式資料保存版](TRADINGVIEW_MCP_OFFICIAL_REFERENCE.md) |
| MCP_VERIFICATION_2026-10-18.md | 過去の実機検証 | [検証記録](../archive/MCP_VERIFICATION_2026-10-18.md) |
| RELEASE_CANDIDATE.md | 過去のリリース準備記録 | [RC Gate・判定履歴](../archive/RELEASE_CANDIDATE.md) |
| SECOND_PC_ACCEPTANCE_TEST.md | 過去の受入手順 | [PR #29向けの受入手順](../archive/SECOND_PC_ACCEPTANCE_TEST.md) |
| RELEASE_NOTES_0.1.0b1.md | リリースノート | [未公開の案](../release/RELEASE_NOTES_0.1.0b1.md) |

新設の[トラブル対応](../user/TROUBLESHOOTING.md)は、導入・認証・結果比較・同期・Taskの失敗時の入口です。旧READMEの過去のPhase別説明は現在の操作マニュアルへ重複掲載しません。

[文書一覧](../README.md)
