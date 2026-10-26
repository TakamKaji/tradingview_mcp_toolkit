# develop-first運用：開発PRと配布工程を分ける

`develop`はテスト・開発資料を含む開発正本、`main`は利用者に渡す配布構成。**開発・文書修正は原則developから開始し、実装・テスト・レビューを1本のdevelop向けPRで完結させる。** main同期はdevelop向けPRのマージ後、配布が必要になった時だけ行う別工程であり、毎回2本のPRを同時作成しない。

関連：[Issue #33](https://github.com/TakamKaji/tradingview_mcp_support/issues/33)（配布・Release）、[Issue #32](https://github.com/TakamKaji/tradingview_mcp_support/issues/32)（Public公開前監査）。

## 作業の入口

- **すべての開発・文書修正**：原則最新`develop`から作業ブランチを作る。READMEや共通利用者ガイドも同じ。既存develop向けPRを継続する依頼では、そのbase/head・既存コミットと未コミット変更を確認して保持する。
- **変更と検証**：配布可能な変更とテスト・開発資料・開発設定を別コミットに分け、develop向けPR内で実装・検証・レビューする。通常の作業完了にmain向けPRの同時作成を含めない。
- **後日の配布**：develop向けPRのマージを確認し、必要な場合だけmainから別の配布作業ブランチを作る。配布対象コミットを選択的に取り込み、配布差分をレビューする。main/develop本体へ直接pushしない。

## コミットを分ける（重要）

例えば`feat/issue-XX`で次のように作る。

1. **A: 共通・配布可能な差分**：`src/`、必要な起動ファイル・JSON・利用者マニュアル等。テストや開発専用資料を混ぜない。
2. **B: 開発専用**：`tests/`、`docs/development/`、`docs/archive/`、開発用`AGENTS.md`・`CLAUDE.md`・`GEMINI.md`、開発設定・検証記録など。

AとBを`develop`向けPRで検証・レビューする。そのPRをマージした後、配布が必要な時だけ**Aだけ**を元のコミットSHAで`cherry-pick -x`等により選択する。PRのマージ方式によりSHAが変わる場合も、配布対象だけのコミットを特定できるよう記録し、開発専用差分を含むsquashコミットを丸ごと取り込まない。Bを拾ってからファイル削除する方式は避ける。

`main`は機能実行と利用に必要なファイルだけを保つ。`tests/`、`docs/development/`、`docs/archive/`、`.codex/`、`.claude/`、`scripts/development/`、開発依存・検証ツールを持ち込まない。必要物は実際の`main` treeを見て決める。

**Issue #58の例外：ルートの`GEMINI.md`・`AGENTS.md`・`CLAUDE.md`は、配布利用者向けの短い入口に限りmainへ収録できる。** READMEと`docs/user/AI_JSON_GUIDE.md`への導線、母集団/完全性・Provider対応・実行結果の検証・明示依頼のないWrite禁止だけを案内し、詳細は共通ガイドを正本とする。モデル役割分担、subagent、実装/テスト指示、開発設定は配布しない。developの同名ファイルをそのままcherry-pickせず、共通利用者文書のコミットと各ブランチの入口コミットを分離する。

## develop → main の例

これは**develop向けPRマージ後、main反映が必要になった場合だけ**行う別の配布工程の例。配布可能な共有コミットAと、その検証済み内容・マージ状態を確認する。配布用PRはmainから切る別の作業ブランチで作り、通常の開発PRと同時作成しない。mainへの取り込み・Public化・tag・Releaseは個別の依頼範囲で判断する。

```sh
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c release/issue-XX

# develop側の「配布対象だけ」の元コミットA
git cherry-pick -x <COMMIT_A_SHA>

git diff --check
git diff --name-only origin/main...HEAD
git diff --name-only origin/main...HEAD -- tests docs/development docs/archive .codex .claude scripts/development requirements-dev.txt
# 配布候補の全treeにも開発専用資産がないこと（出力なし）
git ls-tree -r --name-only HEAD -- tests docs/development docs/archive .codex .claude scripts/development requirements-dev.txt
# 入口は存在だけで合格にせず、上記の短い利用者向け例外に合う本文を確認する
git diff origin/main...HEAD -- AGENTS.md CLAUDE.md GEMINI.md
```

開発専用パスの差分・全tree列挙は**出力が空**であること。入口の差分は内容を確認し、ファイル名だけで開発用入口を許可しない。依存定義に開発依存が混入していないこと、入口と共通ガイドの相対リンク、現行BATパスも確認する。`cherry-pick`で競合したら自動解決を信用せず、配布対象の差分・実装とテストの契約を再検証する。

```sh
# 競合を手作業で適切に解決した場合だけ
git add <RESOLVED_FILES>
git cherry-pick --continue

# 解決できない／取り込み対象が間違った場合
git cherry-pick --abort
```

main向けPRに元コミットAのSHA、追加した検証結果と省略した開発専用コミットBを記載。`-x`の`(cherry picked from commit ...)`を残す。元と先のSHAが違うことは正常で、必要なら`git show`／Git blob SHAで**配布対象ファイルの中身が同じこと**を確認する。

## 既存develop向けPRを継続する場合

- GitHub上のbase/head/SHAとローカル・remote-tracking refsを照合し、既存コミットを保持して同じheadへ追加commit・通常pushする。不要な作り直し・force pushをしない。
- 既に同じ作業のmain向けPRがある場合、一本化の依頼に従って理由と後日の選択的取り込み方針を本文・コメントに残し、マージせずCloseする。共有元コミットとdevelop側の取り込み先を記録し、後日重複適用しない。
- main用入口とdevelop用開発指示の用途差を維持し、ブランチ間の全文コピーやdevelop全体のmainへのmergeをしない。

## PR・検証・公開の境界

- **実装**：developで関連pytest/ruff、配布側で必要なWindows/Docker実行確認。変更のない機能を毎回全件再テストする必要はない。未実施のライブ確認は未実施と書く。
- **文書のみ**：リンク・見出し・CLI例、`git diff --check`を確認。無変更コードの全件pytestやDocker再buildは原則不要。
- **絶対にしない**：`develop`ブランチ全体を`main`へmerge、`git merge develop`、履歴書換え・force push、不要な開発資産のmain混入。
- **公開前Gate**：[公開前チェック](PUBLIC_RELEASE_AUDIT.md#issue-58の配布入口チェック2026-10-25追記)でも上記の短い利用者向け入口だけを例外とし、開発用設定・subagent・テストは除外する。`main`マージはPublic化・tag・Release作成の許可ではない。Issue #32がNO-GOの間は公開操作をしない。
- 新規Issueは実際に残課題がある時だけ作成。マージ済みの作業Issueは証拠を残して閉じ、Provider制約のような未完了事項だけOPEN維持。
