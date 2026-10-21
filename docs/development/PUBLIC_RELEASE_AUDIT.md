# Public公開前監査（Issue #32 / 2026-10-20 JST）

> 本書は2026-10-20時点の監査記録です。2026-10-22の履歴初期化候補では、公式資料の長文転載を公式URLと独自の要約へ置換し、Provider fixtureの説明原文を除去、非公開Drive URLも除去しました。過去のGitHub PR/Issue・キャッシュ等に旧資料が残る可能性は別の公開前リスクです。許諾取得やPublic公開の承認を済ませたとの意味ではありません。

**判定：NO-GO（公開準備は保留）**。公式資料・schema保存物の再公開許諾を確認できず、commit識別情報と非公開Drive文書の公開範囲にも所有者判断が残ります。秘密スキャナーの検出0件だけで公開可能とは判定しません。依頼の段階条件に従い、[Issue #33](https://github.com/TakamKaji/tradingview_mcp_support/issues/33)の配布ZIP実装は開始しません。

対象は[Issue #32](https://github.com/TakamKaji/tradingview_mcp_support/issues/32)、基点mainは`e38a547251d66baeec14a5133755a29bcbf213e3`です。本報告書には検出した個人識別値、秘密値、前後行、署名付きURLを掲載しません。GitHubの記録・設定は監査時点のスナップショットであり、公開直前に再確認が必要です。

## 1. 確認範囲と結果

`CHECKED`は記載した範囲の検査実施を意味し、無制限の安全保証ではありません。`UNCHECKED`をPASSへ読み替えません。

| 対象 | 実施内容・結果 | 状態 |
| --- | --- | --- |
| mainの追跡ファイル | 131ファイル。ソース・tests・fixtures・開発/過去資料・AGENTS・BAT/PowerShell・定義を対象に検査。Gitleaks検出0 | CHECKED |
| GitHubの現在の枝・PR refs | 現存リモート枝2本、取得可能なPR head refs 17本。tag 0。PR merge refsは公開されているものなし。これらから到達する214コミットを確認 | CHECKED |
| ローカルに追加で到達可能な履歴 | 上記に加え2コミットを含む計216コミット、494 tree、387 unique blobを検査。古いローカル枝・remote-tracking refsも対象に含めた。現存GitHub枝2本とローカルの古いrefを混同しない | CHECKED |
| 履歴の秘密検査 | Gitleaks 8.30.1、全refのpatch検査は196コミットを走査。mergeでpatchに出ない内容も全387blobの独立内容検査で補完。両方検出0 | CHECKED |
| 追加のパターン検査 | 秘密鍵・既知token/JWT・メール・個人パス・ローカルURL・credentialキー・LFS pointerを全blobで補完。credential文字列候補84件はすべてtestsの短い固定値・記号placeholderとして区別。認証secretの実在を確認したものなし | CHECKED / 検出限界あり |
| commit author/committer | メール識別子2種類、うちGitHub noreply以外が1種類。名前識別子3種類。値は再掲せず、公開同意を所有者が確認する | 要所有者判断 |
| Git LFS・submodule・symlink | 全blobにLFS pointerなし。現在のtreeにsubmodule/symlinkなし。到達可能履歴に画像・PDF・Office・ZIP・実行バイナリのpathなし、NULを含むbinary blobなし | CHECKED |
| Issue/PR本文 | Issue 16件・PR 17件（合計33記録）、open/closed両方をAPIで列挙 | CHECKED |
| コメント・レビュー | 通常コメント33件、レビュー3件、inline reviewコメント0件、commitコメント0件。本文・title等136 text fieldにGitleaksと補助検査を適用、secret検出0 | CHECKED |
| GitHub添付 | 列挙できた本文・コメント内のGitHub添付URLは0件。削除済み・編集前の添付が存在しなかったことまでは保証しない | CHECKED / 過去削除物はUNCHECKED |
| 外部文書 | Drive正本へのリンク1件。接続ツールでowner-onlyの非共有ファイルと確認。2032行を読み取り、秘密鍵・既知token・個人パスの補助検査では検出0。公開・共有変更は実施せず、公開同意とリンク存置の判断は未了 | 要所有者判断 |
| Actions | workflow 0、run 0、artifact 0をAPIで確認。存在するログ・artifactの内容検査対象はなし。既に削除・期限切れの内容は取得不能 | CHECKED / 失効物はUNCHECKED |
| その他GitHub公開面 | Release 0、tag 0、deployment 0、webhook 0。Wiki/Discussions/Pagesは無効 | CHECKED |
| 権利・再配布 | 自作部分のMIT、実環境の依存48 distributionのmetadataと付属licenseを確認。公式資料の長文転載とschema snapshotの再公開許諾は未確認 | BLOCKED |
| 配布ZIP | 設計上の必要物・除外範囲をIssue #33と照合。生成・展開・Windows setup/MCP smokeは未実施 | NOT STARTED |

secret候補が0であることと、個人識別情報・権利上の公開判断が済んだことは別です。認証が有効か確かめる外部リクエストや、credential/tokenの削除・rotationは行っていません。

## 2. 再現方法と検出限界

Windows Embedded Python 3.12.8（`setenv.bat`経由）とGitleaks 8.30.1を使用しました。Gitleaksは[公式のv8.30.1配布](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1)からWindows x64版を検証領域に取得し、配布元checksumsのSHA-256 `d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e`とZIPの一致を確認しました。OSへのインストールや依存の追加はしていません。

監査時の主要コマンド（公開直前は最新refsを再取得し、redact済みレポートもGit管理外へ置く）：

```text
git fetch origin "+refs/heads/*:refs/remotes/origin/*" "+refs/pull/*/head:refs/remotes/audit-pr/*" "+refs/pull/*/merge:refs/remotes/audit-pr-merge/*" --tags
git rev-list --objects --all
gitleaks git . --log-opts="--all" --redact=100 --no-banner --report-format=json --report-path=.local/audit32/gitleaks_history.json
```

標準ライブラリの一時スクリプトで、`git cat-file --batch`から全unique blobを取得し、hash名の検証ファイルへ書いて`gitleaks dir`でも検査しました。HEADは`git ls-tree -rz HEAD`の追跡ファイルだけを別コピーへ展開して独立検査しています。`.local/`、runtime、credential、結果をスキャナー対象の配布コピーへ混入させていません。GitHub本文はメモリから`gitleaks stdin --redact=100`へ渡し、報告は件数だけにしています。検査ツールと生のAPI応答はリポジトリに収録しません。

通常のGitleaks既定ルールはパターン・entropy・allowlistに依存します。独自形式、暗号化/分割/変形した秘密、低entropyパスワード、画像内情報を網羅的に証明できません。全blob検査でmerge内容を補完しても、内容をhash名にした検査では元path限定ルールの意味は保持しないため、元path付きpatch検査と併用しています。

到達不能でサーバー側に残るobject、取得できない削除済み枝、削除・編集前のIssue/コメント、既に期限切れ・削除されたActionsログ/artifact、外部fork・第三者キャッシュ・過去のダウンロードは`UNCHECKED`です。GitHubが保持するすべての非公開内部記録を取得したという主張はしません。将来の追加commit・新規PR・新しい依存解決結果も今回の合格対象ではありません。

## 3. Blocker / Major / Minor

### Blocker B1：第三者資料の再公開許諾が未確認

[公式リファレンス保存版](TRADINGVIEW_MCP_OFFICIAL_REFERENCE.md)には公式ページの長文コピーがあり、過去のcommitにも残っています。`tests/fixtures/`の2件のinputSchema snapshotにもProviderの説明文があります。出典記載や自作コードのMITだけで、第三者の説明文全体までMIT許諾を得たとは扱えません。

[TradingView利用規約](https://www.tradingview.com/policies/)の権利・データ利用条項と[Copyright and fair use rules](https://www.tradingview.com/support/solutions/43000591349-copyright-and-fair-use-rules/)、[MCP公式ページ](https://www.tradingview.com/mcp/docs)を2026-10-20に確認しました。今回調べた範囲では、この転載・snapshotの一般向け再配布を許諾する根拠を確認できていません。これは違反を断定する法律判断ではなく、Issue #32の「許諾不明の転載をGOにしない」基準による停止です。

対応案は、まず所有者が許諾根拠を確認することです。確認できなければ、長文転載を出典リンクと独自の最小限の要約へ置換し、fixtureも必要最小限の独自schema/検証方法へ整理する案を別作業で検討します。**最新treeの置換だけでは、履歴の転載は公開対象に残ります。** 既存履歴を含めて公開可能と判断できない場合は、非公開原本を保持した公開用の別履歴・別リポジトリ等を所有者が選択する必要があります。今は削除・履歴改変・リポジトリ再作成を行いません。

### Major M1：commit識別情報・非公開文書の公開判断

noreply以外のメール識別子、author名、個人利用の判断や開発運用記録が公開履歴に含まれます。実際の値をここへ複製しません。所有者と該当contributorが公開範囲を確認してください。今後のcommitをnoreplyへ変えても既存履歴は変わりません。

Drive正本は監査時点で非共有でした。コードのPublic化だけでDriveの共有設定が変わるわけではありませんが、ファイル識別子と存在へのリンクは露出します。本文のRepository版、リンク、Issue/PRに含む運用経緯を公開する判断を、Driveの共有変更と分けて確認してください。

### Major M2：GitHubセキュリティ機能の未確認・未設定

APIでsecret scanningとDependabot alertsが無効と応答されました（それぞれ404/403。alertが0件という意味ではありません）。code scanningは403で検査不能。`security_and_analysis`は取得応答に含まれず、push protectionの有効性も確認できていません。

mainのbranch protectionとrulesetsはプラン制約の403で、保護されていると判定しません。fork PR実行承認ポリシーも現在のAPIで確認できていません。Public公開前後の機能利用条件を所有者が確認し、利用可能な保護、secret scanning、push protection、Dependabot、mainへの必須レビューを設定・検証する必要があります。設定変更は本監査では行いません。

Actionsは有効、全action許可、SHA pin必須はfalseでした。既定workflow token権限はread、PRレビュー承認権限はfalseです。現在workflowはないため、外部actionを実行する既存コードはありません。今後追加するなら手動buildのみ・`contents: read`・actionのfull commit SHA固定・artifact内容の検査を基本とし、外部PRやコメントを信頼して秘密付き実行をしない方針を定めます。

### Minor・継続Gate

- [.gitignore](../../.gitignore)はruntime・結果・ローカル状態・生成物を除外していました。今回`.env`、一般的な鍵拡張子、rootのcredential/token JSONの誤追加防止を追加しました。すでに追跡済みのファイルや`git add --force`には効かず、スキャンの代替にはなりません。
- READMEへ非公式・非提携の第三者ツールである旨を追加しました。公式ロゴ、スクリーンショット、画像バイナリは現在と到達可能履歴で見つかりません。名称の表示目的と商標上の判断は所有者が確認し、公式製品との誤認を避けます。
- 依存は[別表](PUBLIC_DEPENDENCY_LICENSES_2026-10-20.md)の観測版を確認しました。将来版・別OS解決・binary再配布の自動承認ではありません。
- 独立した新規Windowsユーザーでの初回OAuthは未検証のままです。全米株Provider制約、`us_sector_morning.enabled=false`、S&P 500限定503件と全米株未対応の区別も維持します。

## 4. Publicリポジトリと実行ZIPの違い

Public化ではmainだけでなく、アクセス可能なbranches、PR refs、Git履歴、Issue/PR・コメント等も露出対象です。開発資料を別ブランチへ移したり、実行ZIPから除外したりしても、同じPublicリポジトリで非公開にはできません。[GitHub公式の可視性変更説明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility)は、コードの閲覧・forkとActions履歴/ログの公開を明示しています。後でPrivateへ戻しても第三者が既に取得したコピーは回収できません。

Issue #33の実行ZIPは、特定commitから許可リストでBAT・PowerShell・実行コード・依存定義・LICENSE・利用者文書を収録する別成果物です。tests・開発/過去資料・開発ツール・runtime・`.local/`・credential・結果は除外します。GitHub自動のSource code ZIPとは別物です。今回はBlocker B1が未解決のため、ZIP生成スクリプト、Actions、配布用リンク変換の実装・試験に着手していません。

## 5. 所有者の判断と次のGate

1. B1の第三者資料・schema保存物について、既存履歴を含めた公開許諾の根拠または対応方針を決める。
2. commit識別情報、非公開Drive文書へのリンク、開発・検証履歴の公開範囲を確認する。
3. GitHubのセキュリティ設定の未確認項目を確認し、必要な変更を別途承認・検証する。
4. 上記を反映した最新の公開候補を再監査し、GOになってからIssue #33を別ブランチで実装する。
5. 生成ZIPの再現性・禁止物・リンク・展開後Windows動作を検証し、未実施の初回OAuthなどをRelease前Gateに残す。
6. Public化・tag・Release公開・mainマージは、今回の準備とは別に所有者が明示判断する。

実secretが後から見つかった場合は、値を再掲せず対象credentialを失効・rotationする判断を優先します。履歴書き換え、コメント・runの削除、リポジトリ作り直しは、影響と回復方針を提示して明示承認を得た別作業にします。

## 6. 今回の変更と検証

監査報告、依存ライセンス表、開発索引、READMEの非提携表示、`.gitignore`の誤追加防止だけを変更しました。機能コード・CLI・依存定義・Job設定・Drive本文/共有設定・GitHub設定は変更していません。MCP/Watchlist/Alert Write、Scheduler登録・削除、初回OAuth、ZIP setup smoke、Release生成は実行していません。

GitleaksのHEAD・全ref patch・全blob・GitHub本文・今回の変更5ファイルの検査はすべて検出0、終了コード0でした。補助パターン検査、API列挙、実環境ライセンス調査も実施しました。47 Markdownの相対リンク393件・アンカー171件とignoreの14条件、変更範囲が監査/文書/ignoreの5ファイルだけであることを確認しました。`git diff --check`も成功です。文書とignoreだけのため、pytest/ruffの全件再実行は行っていません。

## 参照

- [GitHub Secret scanning：検出範囲と利用条件](https://docs.github.com/en/code-security/concepts/secret-security/secret-scanning)
- [GitHub Actions Secure use](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub Push protection](https://docs.github.com/en/code-security/concepts/secret-security/push-protection)
- [開発索引](README.md)
