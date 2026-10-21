# 2ブランチ運用：共有コミットをcherry-pickする

`develop`はテスト・開発資料を含む開発正本、`main`は利用者に渡す配布構成。**同じ変更を両ブランチで二重実装せず、片方で作った配布対象コミットをもう一方へ`git cherry-pick -x`する。**

関連：[Issue #33](https://github.com/TakamKaji/tradingview_mcp_support/issues/33)（配布・Release）、[Issue #32](https://github.com/TakamKaji/tradingview_mcp_support/issues/32)（Public公開前監査）。

## 作業の入口

- **Python本体・認証・Job・Docker等の機能変更**：原則`develop`から作業ブランチを作り、実装・テストする。配布対象のファイルだけを**独立したコミット**にする。テスト・開発資料などは別コミット。
- **READMEや利用者向け文書だけ**：`main`先行でもよい。両方に必要な変更は`develop`側の作業ブランチへ逆方向にcherry-pickする。配布構成と開発構成で文章に違いがあれば無理にcherry-pickせず、差を明示して調整する。
- どちらも直接pushせず、対象ブランチへPRを作る。PRがマージ済みか・最新HEADかを確認してから同期する。

## コミットを分ける（重要）

例えば`feat/issue-XX`で次のように作る。

1. **A: 共通・配布可能な差分**：`src/`、必要な起動ファイル・JSON・利用者マニュアル等。テストや開発専用資料を混ぜない。
2. **B: 開発専用**：`tests/`、`docs/development/`、`docs/archive/`、`AGENTS.md`、開発設定・検証記録など。

AとBを`develop`向けPRで検証する。`main`向けには**Aだけ**を元のコミットSHAでcherry-pickする。Bを拾ってからファイル削除する方式は避ける。Aに開発用差分が混ざったら、ソース側でコミットを分割し直してから持っていく。

`main`は機能実行に必要なファイルだけを保つ。特に`tests/`、`docs/development/`、`docs/archive/`、`AGENTS.md`、`.codex/`、開発依存・検証ツールを持ち込まない。必要物は実際の`main` treeを見て決める。

## develop → main の例

`develop`側で実装・テストし、共有コミットAのSHAを控える。配布用PRは**mainから切る別の作業ブランチ**で作成する。

```sh
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c release/issue-XX

# develop側の「配布対象だけ」の元コミットA
git cherry-pick -x <COMMIT_A_SHA>

git diff --check
git diff --name-only origin/main...HEAD
git diff --name-only origin/main...HEAD -- tests docs/development docs/archive AGENTS.md .codex
```

最後のコマンドは**出力が空**であること。その他の開発専用ファイル・不要な差分がないことも個別確認する。`cherry-pick`で競合したら自動解決を信用せず、配布対象の差分・実装とテストの契約を再検証する。

```sh
# 競合を手作業で適切に解決した場合だけ
git add <RESOLVED_FILES>
git cherry-pick --continue

# 解決できない／取り込み対象が間違った場合
git cherry-pick --abort
```

main向けPRに元コミットAのSHA、追加した検証結果と省略した開発専用コミットBを記載。`-x`の`(cherry picked from commit ...)`を残す。元と先のSHAが違うことは正常で、必要なら`git show`／Git blob SHAで**配布対象ファイルの中身が同じこと**を確認する。

## main → develop の例

利用者向けREADME修正などを先に`main`の作業ブランチで作った場合、共有コミットCを`develop`へ取り込む。

```sh
git fetch origin
git switch develop
git pull --ff-only origin develop
git switch -c docs/issue-XX-develop-sync
git cherry-pick -x <COMMIT_C_SHA>
git diff --check
git diff --name-only origin/develop...HEAD
```

`develop`に存在する開発資料やリンクを破壊しないことを確認し、develop向けPRを作る。README全文を両ブランチで手編集して別内容にする運用は原則避ける。

## PR・検証・公開の境界

- **実装**：developで関連pytest/ruff、配布側で必要なWindows/Docker実行確認。変更のない機能を毎回全件再テストする必要はない。未実施のライブ確認は未実施と書く。
- **文書のみ**：リンク・見出し・CLI例、`git diff --check`を確認。無変更コードの全件pytestやDocker再buildは原則不要。
- **絶対にしない**：`develop`ブランチ全体を`main`へmerge、`git merge develop`、履歴書換え・force push、不要な開発資産のmain混入。
- **公開前Gate**：`main`マージはPublic化・tag・Release作成の許可ではない。Issue #32がNO-GOの間は公開操作をしない。
- 新規Issueは実際に残課題がある時だけ作成。マージ済みの作業Issueは証拠を残して閉じ、Provider制約のような未完了事項だけOPEN維持。
