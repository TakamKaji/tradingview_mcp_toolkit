# 初回Public Release再監査（2026-10-31 JST）

**公開判定：NO-GO。配布候補の準備・実機確認は完了した範囲を以下に記録するが、公開許諾・独立受入の完了を意味しない。** 管理は[Issue #33](https://github.com/TakamKaji/tradingview_mcp_support/issues/33)へ集約する。[旧監査](PUBLIC_RELEASE_AUDIT.md)と[Issue #32](https://github.com/TakamKaji/tradingview_mcp_support/issues/32)のCLOSED状態を公開PASSへ読み替えない。

| 対象 | 今回固定した値 |
| --- | --- |
| 配布main | `d5f3536f12c1743562082fc64e1629143a36f8ee` |
| 開発develop | `e9c8b00a998870a31cfc8cbf306fc55335f533d7` |
| バージョン候補 | package `0.1.0b1` / 将来のtag候補 `v0.1.0b1` |
| 配布方式 | GitHub標準Source code (zip)。今回は同じmain SHAのGitHub zipballを取得・検査 |
| GitHub状態 | Private、default branch main、tag 0、Release 0、OPEN PR 0（作業PR作成前） |
| 残Issue | OPENは #33・#58・#70。新しいIssueは作らない |

## 1. 調査範囲・再現性

2026-10-31に`git fetch`と`git ls-remote origin`で現存refsを列挙した。**現存GitHubの7 heads・47 PR head refs・0 PR merge refs・0 tags**のSHA集合から到達する335 commits、777 trees、611 unique blobsが対象。古いローカルbranchやremote-tracking refは、この件数へ加算していない。

- heads：main、develop、`codex/issue-58-python-guide-main`、`codex/mcp-feature-parity-audit`、`codex/official-mcp-manual-catalog`、`docs/main-official-mcp-acceptance-20261027`、`test/codex-prime-sma25-20261027`。残存branchは削除していない。
- GitHub REST APIをページ末尾まで取得：Issue 25件＋PR 47件、通常コメント59件、review submission 15件、inline reviewコメント0、commitコメント0。本文・title等312 text fieldとcommit messageを検査。PR差分で参照される旧ファイルは到達可能blob検査に含む。
- Actions：Dependency Graphのdynamic workflow 1、成功run 1、job 1の取得可能ログを確認。artifact 0、deployment 0、webhook 0、Release 0。Wiki・Discussions・Pages無効。
- Git LFSの実pointer 0、NULを含むbinary blob 0、mainのsymlink/submodule 0。列挙したGitHub本文中の添付URL 0。履歴内のLFS説明文へのパターン一致を実pointerと誤認しない。

既存のGitleaks 8.30.1を再使用。旧取得時の配布元・ZIP checksum記録を保持し、今回使用したexeのSHA-256は`17157e2ee8b76fc8b1d8bee607a250e34b8a8023c8bc81822d4b5ee4d78fcb7c`。次の4範囲はすべてexit 0・検出0：現存refsを明示したGit patch、611 blobの独立コピー、mainの追跡内容、Issue/PR/コメント/レビュー/commit message/取得済みActionsログの公開対象コーパス。mergeでpatchに現れない内容をblob検査で補完した。

管理APIの応答には一時clone credentialが含まれ、管理メタデータ全体への検査で1件検出した。これは公開対象本文や追跡履歴への漏洩検出とは区別する。値・前後行を報告へ転記せず、API応答・secret検査ログ・Drive識別子・著者情報はGit管理外にのみ保持した。認証値の有効性試験、失効・削除は行っていない。

主な再現手順は、現存refsの取得→SHA集合で`git rev-list --objects`→`git cat-file --batch`で全blobを検査→ページ送り付きAPI列挙→公開対象本文と取得可能runログを検査、の順。生証跡と補助スクリプトはローカル`.local/release-audit-20261031/`、実機配布コピーは`.local/rc31/`に保持する。これらをcommit・Issueへ添付しない。

**限界：** Gitleaksの検出0は秘密の不存在や著作権許諾の証明ではない。独自形式・低entropy・分割/暗号化値、GitHub内部の到達不能object、編集前/削除済み本文、削除済み添付、期限切れ/削除済みActionsログ、外部fork・第三者cacheはUNKNOWN。将来のcommit・依存解決・公開設定変更後は今回の固定スナップショットから外れる。

## 2. B1：公式資料とSchema — NO-GO

履歴整理の効果は確認できた。mainは2026-10-22の独立root `85a7ee91c0cfeb8e4e4c6551ca1d3645c6fd00f7`から24 commits、developは同日の独立root `4770970d2d65ea7e3971bbfea87bc1b43aa9fc39`から58 commits。現存7 headsの到達履歴に、下記の旧495行版blobは含まれない。

現在のmainには公式資料保存版・fixtureはない。develop側の公式参照文書は79行の公式URL・独自要約・互換アンカーで、旧配置220行は移動案内。fixtureは構造テスト契約へ置換され、Providerの説明原文を除去している。残る`description`プロパティはWatchlist入力のフィールド名で、転載説明文ではない。2026-10-27のfixtureも構造契約である。

**一方、取得可能な旧PR refsに置換前の内容が実在する。** 例：PR #34 headの`docs/development/TRADINGVIEW_MCP_OFFICIAL_REFERENCE.md`は495行、同refの2026-10-18 inputSchema fixtureは876行・`description`キー111箇所。旧495行版blobはPR #31・#34・#36・#37・#38・#39・#41・#42・#43・#44・#45のhead到達履歴に残る。本文やSchemaそのものはこの報告へ再掲しない。

したがって「最新treeで置換済み」「10月22日以前のbranch履歴を切り離した」は確認済みだが、**既存リポジトリ全体から旧資料が消えたとは判定できない**。[TradingView利用条件](https://www.tradingview.com/policies/)と[公式MCP資料](https://www.tradingview.com/mcp/docs)を再確認したが、当該転載物の一般再配布を許諾する根拠は今回も確認していない。構造契約・独自要約・MCPデータ利用についても、プロジェクトのMITで第三者の権利まで許諾されたとは扱わない。

解消には、残存する資料・履歴・GitHub公開面を含む許諾根拠の確認、または所有者承認済みの対応後に取得不能/公開対象外になったことの再監査が必要。単なる枝削除や再度のforce pushはPR refsを消す証明にならない。GitHub Supportへの相談、Private継続、既存原本を保持する別公開履歴は判断材料であり、削除保証や実行承認ではない。今回、履歴書換え・ブランチ削除・旧記録削除・別Repo作成はしていない。

## 3. M1：識別情報・Drive・開発記録 — 要所有者判断

- 現存refs到達commitのauthor/committerに名前識別子4種類・メール識別子3種類。うちnoreplyを含むもの2種類、それ以外1種類。値は再掲しない。将来のcommitをnoreplyにしても旧記録の公開範囲は変わらない。
- 現存7 headsの追跡文書にはDrive URLを検出しなかったが、旧履歴の5 blobとGitHub本文に同じ外部文書への参照が残る。接続Driveのmetadataを再確認し、`shared=false`、owner権限1件のみだった。共有設定・本文は変更していない。RepoのPublic化でDrive本文の共有は自動変更されないが、文書識別子・存在・開発経緯の露出は残る。
- develop・作業branch・旧Issue/PRに開発上の判断、AI利用・実機検証、銘柄・データ品質の記録がある。main ZIPから除外しても同一Public Repo内の非公開資料にはならない。

旧#33にはブランチ・開発履歴の可視性に関する了承記録があるが、今回の著者情報・旧PR・Drive参照を含む範囲の最終確認や転載許諾まで済んだと拡大解釈しない。所有者が対象者の同意と公開範囲を確認する。

## 4. M2：GitHubセキュリティ — 要所有者判断

| 項目 | 今回のAPI実測 | 判定・残作業 |
| --- | --- | --- |
| main/develop branch protection | 両方`protected=false`。詳細取得はプラン制約403 | 保護なし。PrivateでPro利用または承認済みPublic化直後に設定 |
| Rulesets | プラン制約403 | UNKNOWN。未設定/設定済みを推測しない |
| Collaborators / deploy keys / hooks | collaborator 1件（所有者のみ）、deploy key 0、hook 0 | 確認済み。アカウント全体のApp/PAT/SSH鍵は別確認 |
| Actions permissions | `enabled=false`、SHA pin必須false | Actions無効。過去runが消えたという意味ではない |
| Workflow token | read、PR承認false | 確認済み |
| fork PR承認ポリシー | API 422 | UNKNOWN。Actionsを再度使う前にUI確認 |
| Dependabot alerts | 有効確認API成功、alerts 0 | 旧監査の「無効」から更新。ゼロは脆弱性不存在の保証ではない |
| Secret scanning | API 404、disabledという応答 | 無効。alerts 0と扱わない |
| Push protection | `security_and_analysis`なし | UNKNOWN。UI確認 |
| Code scanning | API 403、not enabledという応答 | 無効。今回コード解析結果を取得したとは扱わない |

設定は一切変更していない。管理者の画面操作と順序は[最終チェックリスト](../release/RELEASE_CHECKLIST_0.1.0b1.md)に集約した。[GitHub公式の可視性変更説明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility)どおり、公開でActions履歴・ログも閲覧可能になる。Actions無効化は過去ログの公開リスク対策を代替しない。

## 5. main配布構成 — 検査範囲はGO

GitHub zipballの80ファイルをmain Git blobと照合し、欠落・余分・内容不一致0。実機セットアップが作るruntime/results等は元ZIPに含まれない。検査したMarkdown相対参照184件・アンカー43件の不整合0。

- ルートBATは`setup.bat`・`app.bat`・`export-results.bat`、内部BATは`scripts/`。Embedded bootstrapと通常Windows Credential Manager使用を確認。ユーザープロファイルの置換なし。
- `tests/`、`docs/development/`、`docs/archive/`、`.codex/`、`.claude/`、`scripts/development/`、開発依存ファイル、runtime、credential、過去resultsの混入なし。MIT LICENSE・pyproject・利用者READMEを保持。
- `AGENTS.md`・`GEMINI.md`・`CLAUDE.md`は短い利用者向け入口。AI共通ガイド、Provider検証注意、自然言語受入ガイドへ到達可能。3製品の新規セッション受入の証拠とはしない。
- `public_sample_screen_daily`は`enabled=false`・`watchlistSync=false`。明示`run`はRead＋保存のみ。setupとDocker既定起動はWrite・Schedulerを実行しない。`sample_screen_daily`は既定で有効・同期ありなので初回確認に使用しない。READMEの注意は現状と整合。
- mainとdevelopは用途上異なる。developのOHLCV追加引数（date/format等）と詳細マニュアルはmainに全部反映されていない。mainの実Schemaを正本にし、「35 Toolあり」を全引数同等・全CLIありと表現しない。develop全体を配布しない。

## 6. Windows・Docker検証

Windows 11 Pro 64-bit上、最新main ZIPを新規フォルダへ展開し、runtimeなしから実施。長い展開先ではpip導入時のパス長制限エラーでsetup exit 1。**同じZIPを短い新規フォルダへ展開するとsetup exit 0**。OSのLong Path設定・環境変数・既存credentialを変更せず回避できた。今回の利用者文書へ手順を追加する。

| 検証 | 結果 |
| --- | --- |
| `setup.bat --no-pause` | 空runtime→CPython 3.12.8・pip・依存導入成功。認証スキップは仕様どおり |
| `app.bat --version` / `--help` / `jobs list` | exit 0、stderr 0、version 0.1.0b1 |
| `mcp status` / `mcp tools` | 保存済みWindows認証でsuccess、35/35 Tool、missing/extra 0、exit 0、stderr 0 |
| `run public_sample_screen_daily` | 2026-10-31 22:34 JSTの新規結果JSON保存、exit 0、stderr 0、errors空、watchlistSyncなし |
| 結果の範囲 | requested limit 50、returned 50、Provider total 1,947、limitReached true、completeCoverage false。上限付き50件であり全件成功ではない |
| `results latest/history` | 今回保存した新しいファイルの日時・内容・履歴を確認、exit 0、stderr 0 |
| CSV / HTML変換 | 両方exit 0・stderr 0、JSON/CSV/HTML各50行。CSV BOM、HTML外部scriptなしを確認 |
| 配布外Pythonへの依存 | 実行Pythonと主要依存は新規runtime、アプリimportは新規src。別環境のsite-packages混入なし。通常Windowsの認証・ブラウザ・TEMP・pip cacheは利用する設計 |
| Docker | 現mainのCompose config成功。Docker/OAuth構成は10月22日rootから無変更。amd64実OAuth・Read・永続化は#40の所有者実測報告を参照し、今回ライブ再実行しない |
| 既存テスト / lint | develop作業ツリーのbootstrap・public sample・export tests：31 passed。Embedded Python経由ruff全件成功 |

CSV/HTMLの初回試行は実行サンドボックスのhard link拒否でexit 1となり、通常Windows権限で同じコマンドを再実行して成功した。製品コードの不具合と混同しない。

**未実施：** 新規Windowsユーザーの初回OAuth、今回のGUIダブルクリック、3種AIの独立新規CLIセッション受入、#70の生成Python・全生データの独立照合、Mac実機・arm64、Dockerライブ再実行。今回の保存済み認証成功は新規ユーザーOAuthの代用ではない。Mac/arm64は初回Releaseの追加必須条件にしない。

新規ユーザーOAuthには所有者が管理する別Windowsアカウントとブラウザ認可が必要で、既存credentialの削除・ユーザープロファイルの置換で模擬しなかった。GUI操作とAI製品別受入は今回のCLI実測から推定しない。#70の元データ一式は今回独立取得していない。文書だけの変更なのでpytest全件・Docker全buildは再実行せず、上記31件と配布実機・Compose検証に限定した。

依存は今回の新規環境43 distribution（アプリ1、runtime40、pip1、build1）を調査し、全件に付属license文書を確認。[今回の版・ライセンス表](PUBLIC_DEPENDENCY_LICENSES_2026-10-31.md)を参照。依存をlockしていないため、将来版や他OSの解決結果までは保証しない。

## 7. Issue整理とRelease条件

| Issue | 確認済み | 残課題と初回Releaseとの関係 |
| --- | --- | --- |
| #33 | 配布構成・今回のWindows検証・候補文書 | **P0/P1の必須ゲート**。公開・tag・Releaseは未承認 |
| #32 CLOSED | 旧監査成果物は残存、今回再監査 | CLOSEDはGOではない。B1/M1/M2を#33で継続 |
| #58 OPEN | #69 main文書反映、#71 JSON優先/外部利用承認、#72 BLOCKED時代替案内はmainに反映。利用者報告で改善あり | 独立した3製品受入は未完。初回βの必須範囲か継続改善とするか**所有者判断**。未確認のまま3製品検証済みを名乗らない |
| #70 OPEN | NAGの疎な日足による25本平均という利用者調査報告を確認 | Core不具合と未確定。注意書きの配布をP1、全生データの独立調査はP2候補。母集団変更・一律除外はしない |
| #18 CLOSED | 全米株Provider制限は文書と無効Jobに残る | CLOSEDを制限解消と扱わない。完全取得を提供すると宣伝しない |
| #40 CLOSED | amd64で所有者が初回OAuth・Read・永続化を確認したコメントあり | 過去の初期検証文書の「ライブ未検証」だけを現在判定に採用しない。Mac/arm64とは区別 |

## 8. 今回の変更と次の判断

共有修正は利用者文書3件だけ（短い展開先・パス長エラー対処・日本株の取引所/低流動性注意）。開発専用の監査・依存表・Release Notes・チェックリストは別commitにする。**develop向けPRをレビュー・承認後にマージし、配布時に共有修正だけをmainへ選択反映する。** 現main SHAは検証済み候補の基点であり、文書修正反映後の最終SHAは再固定が必要。

配布可能な共有commitは`6fefe7d12f064e40ec4817872706e7ca59889366`。監査文書等を含む後続commitはmainへ取り込まない。変更文書10件の相対参照109件・アンカー22件、Gitleaks追加文書検査、`git diff --check`は成功した。

- **P0（Public化前）**：B1の旧PR refsの転載物に対する許諾/対応を解決。M1の識別情報・Driveリンク・開発記録の公開範囲を確認。M2のUNKNOWNと設定順序を所有者が確認し、公開範囲を再監査。
- **P1（初回Release前）**：共有文書を配布mainへ選択反映・標準ZIPの再照合。新規WindowsユーザーOAuthを検証するか、未検証βとして扱う明示判断。#58の必須受入範囲の明示判断。最終SHA・Notesを確定し、別途tag/Release承認。
- **P2候補（公開後でもよい範囲は所有者判断）**：#70の独立データ監査、#58の残る製品別受入、Mac/arm64、将来Provider変更・依存解決の再確認。未完了を閉じない。

リリース候補資料：[Release Notes](../release/RELEASE_NOTES_0.1.0b1.md) / [最終チェックリスト](../release/RELEASE_CHECKLIST_0.1.0b1.md)。Public化・設定変更・tag・Release・main/develop直接push・PR merge・履歴変更・既存記録削除は今回実施していない。
