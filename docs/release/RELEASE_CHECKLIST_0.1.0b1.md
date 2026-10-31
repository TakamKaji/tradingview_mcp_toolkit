# v0.1.0b1 発行前チェックリスト（未承認）

2026-10-31時点は**NO-GO**。[再監査](../development/PUBLIC_RELEASE_REAUDIT_2026-10-31.md)と[Issue #33](https://github.com/TakamKaji/tradingview_mcp_support/issues/33)が現在の判断根拠。以下は所有者が承認後に進める順序であり、公開操作の承認や実施記録ではない。

## 1. Privateのまま解決・判断する

- [ ] B1：旧PR head refsに残る公式資料・Schema説明文を含む再公開許諾の根拠、または承認済み対応後の再監査を記録する。branchの最新treeの置換だけでは完了にしない。
- [ ] M1：commit著者識別情報、旧Driveリンク、開発・AI利用・データ検証記録の公開範囲を所有者と対象contributorが確認する。値をIssueへ貼らない。
- [ ] M2：下記の管理UIのUNKNOWN項目を確認し、公開直後に必要な設定を決める。GitHub FreeのPrivateで使えない保護を事前設定済みとしない。
- [ ] 新規Windowsユーザーで初回OAuthを実測するか、未検証を明記するβとして扱う判断を#33に記録する。保存済みcredential成功で代替しない。
- [ ] #58の独立3製品受入を初回βにどこまで要求するか決める。利用者報告と独立監査を区別し、未完了項目を閉じない。#70の全生データ監査は継続課題でありCore修正済みとは書かない。

## 2. レビュー済みの配布候補を固定する

- [ ] develop向けPRを所有者がレビュー・承認後にマージ。共有の利用者文書commitと開発専用監査commitを保持する（両方をまとめたsquashをmainへ取り込まない）。
- [ ] main起点の配布branchへ**共有文書3件のcommit `6fefe7d12f064e40ec4817872706e7ca59889366`だけ**を`git cherry-pick -x`し、main向けPRをレビュー・承認後にマージ。develop全体のmergeや直接pushをしない。
- [ ] mainの最終SHAを#33とRelease Notesに記録。現在の実機検証基点は`d5f3536f12c1743562082fc64e1629143a36f8ee`。文書反映でSHAが変わるので、現時点で最終版と宣言しない。
- [ ] 最終SHAのGitHub標準ZIPを取得し、全tree、必要BAT・README・LICENSE・Schema・安全なサンプル・相対リンク・禁止物を照合。独自ZIP生成器やActionsを追加しない。
- [ ] 文書だけの反映なら変更文書・リンク・配布構成を再確認。実行コード/依存が変わった場合は該当Windows smokeを再実施する。main/developの用途差を保つ。
- [ ] 最新refs、Issue/PR/レビュー、Actionsログ、共有状態を再監査し、P0が解消してGOになった根拠を残す。GOでも次の公開操作は別途明示承認を必要とする。

## 3. 管理者UIの場所と操作

| 場所 | 確認・設定する内容 |
| --- | --- |
| Repository Settings → Collaborators / Access | 所有者以外の権限、招待中ユーザーを確認。今回collaboratorは所有者のみ |
| Repository Settings → Deploy keys / Integrations、個人Settings → Applications / Developer settings / SSH and GPG keys / Password and authentication | App/PAT/SSH鍵のアクセス範囲、2FA/passkey、不要な権限を所有者が確認。今回アカウント全体は未監査。削除・変更は別途承認 |
| Repository Settings → Rules → Rulesets（またはRulesets） | main/developを対象、Enforcement Active、PR経由必須、force push禁止、削除制限。不要なbypassを設けない。承認可能な他reviewerがいない個人運用ではrequired approvalsを0とする判断を記録。存在しないCIを必須checkにしない |
| Repository Settings → Actions → General | 現在は無効を確認。将来有効化するときは既定token read、PR承認不可、fork実行承認とsecrets/write token制限を確認。fork承認APIの422を設定済みと扱わない |
| Repository Settings → Advanced Security（Security and analysis等、利用中UIの名称） | Dependabot alerts有効を再確認。Secret scanning/Secret Protection・Push protectionの利用可否と有効性を確認。Code scanningは未導入であり、今回専用pipelineを追加しない |
| Repository Settings → General → Danger Zone → Change repository visibility | **P0解消・最新再監査GO・別途公開承認後だけ**Private→Publicを実施。コード・履歴・Issue/PR・Actionsログの露出を最終確認 |

Rulesetsは[GitHub公式](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository)によればFreeのPublic、Pro等のPrivateで利用可能。今回のPrivateはAPIでupgrade要求403だった。Privateで保護を整備できない場合、**公開承認→Public化→直ちにmain/developのbranch保護とセキュリティ設定→読み戻して有効確認→tag/Release**の順にする。公開前に設定できたと記録しない。[公開による影響](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility)は保護設定だけでは取り消せない。

## 4. 承認後のtag・Release発行

- [ ] 最終SHA、`pyproject.toml`の`0.1.0b1`、候補tag `v0.1.0b1`が一致し、同名tag/Releaseがまだ存在しないことを確認する。
- [ ] 所有者から**対象SHAを指定したtag pushとGitHub Release公開の明示承認**を得る。Public化の承認だけをtag/Release承認とみなさない。
- [ ] 承認済みSHAへtagを作成・pushし、[Notes案](RELEASE_NOTES_0.1.0b1.md)の編集用注記を外してGitHub Releaseへ掲載する。初回βとして**pre-release**扱いを選ぶ。検証範囲・既知の制限は残す。
- [ ] GitHub生成のSource code (zip)を実際に取得し、tagの内容・対象SHA・必要物・禁止物を再照合する。GitHub生成tar.gzと独自のruntime同梱ZIPを混同しない。
- [ ] 公開後のsecret scanning結果・branch保護・Push protection・Dependabotを読み戻して記録する。追加alertは内容を転載せず対処判断する。
- [ ] #33に最終SHA・tag・Release URL・検証結果を記録。残る#58/#70は完了条件を満たすまでOPENを維持する。

Public化、tag/Release発行、PR merge、履歴書換え、既存記録削除は、このチェックリスト作成によって許可されない。
