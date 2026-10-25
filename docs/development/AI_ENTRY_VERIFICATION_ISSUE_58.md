# Issue #58：AI入口・判定契約の検証記録

対象：[Issue #58](https://github.com/TakamKaji/tradingview_mcp_support/issues/58)。2026-10-25 JST実施。基点はmain `dace57a`、develop `b56a4ae`。これは文書・入口の検証であり、3製品の遵守やProviderの実取得成功を保証するものではありません。

## ブランチ間の同期と変更範囲

- main `docs/issue-58-ai-entry-main`：共通文書`34c36d8`、短い配布入口`c454240`を分離した。
- develop `docs/issue-58-ai-entry-develop`：`34c36d8`を`cherry-pick -x`した`2e12f78`で共通5文書を同期した。以前のmain側AI文書が未同期のためREADME日英・利用者索引・AI_USAGEの内容競合とAI_JSON_GUIDEのmodify/delete競合が発生。事前に差分が共通AI説明の欠落だけであることを確認し、5文書をmain版へ揃えて解消した。
- 共通5文書は`README.md`、`README.en.md`、`docs/user/README.md`、`docs/user/AI_USAGE.md`、`docs/user/AI_JSON_GUIDE.md`。Git blob比較で同一性を確認する。
- mainの入口は利用者向け。developの既存`AGENTS.md`・`CLAUDE.md`には共通ガイドへの節だけを追加し、開発規則、モデル役割分担、実装/テスト契約を保持した。CLAUDEの旧BATパスも現配置へ訂正した。新規`GEMINI.md`から両方の規則へ接続する。
- developだけで[ブランチ運用](BRANCH_WORKFLOW.md)・[公開前チェック](PUBLIC_RELEASE_AUDIT.md#issue-58の配布入口チェック2026-10-25追記)に短い配布入口の例外と本文審査を追加した。mainへの開発専用コミット同期は行わない。

## 受入条件の確認

| Issueの条件 | 結果・証拠 |
| --- | --- |
| 両ブランチの3入口から共通ガイドへ到達 | 静的リンク検査に合格。mainは各入口を短く保ち、developの既存指示を保持 |
| 製品ごとの読込条件・限界と未実証の明記 | [AI利用手順](../user/AI_USAGE.md#プロジェクトルートでaiを起動する)に公式資料・起動場所・確認手順・下表の制約を記載 |
| 母集団・完全性・Provider・BAT・実行証跡・失敗報告 | [共通ガイド](../user/AI_JSON_GUIDE.md)に契約を追加。successとcompleteCoverageの違いをEngineと照合 |
| 自然言語2文の再現ケース | 原文2文と期待判断をガイドへ収録。実装可能性の確認が先、不能時は根拠と未実行/失敗を報告する判断を確認。実際の各AIへの2文入力・Provider接続は未検証 |
| 4回帰ケースの期待判断・不合格例 | 下表を文書としてレビュー。過去Gemini生成物の問題を不合格とし、実行失敗の全原因は未確定と明記 |
| 相対リンク・BAT・Schema整合性 | 変更Markdownの相対リンク/アンカー、正式BAT5パス、3入口、Schema・サンプルを確認 |
| production動作を変更しない | 両差分はMarkdownのみ。src/・依存・JSON定義・BAT・認証・Job/Watchlist/Schedulerの変更なし |
| main/develop別PR、開発設定を配布しない | 共通文書と入口を分離。main全treeの開発専用パス不存在・入口本文を確認。push/PR識別情報は各PR本文へ記録。自動merge・公開・tag/Releaseは行わない |

## 自然言語入力に対する静的回帰レビュー

| ケース | 確認した期待判断 | 不合格として検出すべき応答 |
| --- | --- | --- |
| 東証プライム全体SMA25乖離率+20%以上 | 元母集団を固定、プライム全件保証と指標対応確認が必須。+方向と確定日足25本・対象日時を明示。未確認なら実行成功とはしない | 出来高上位100件＋手書き代表銘柄を全体とする。OHLCV失敗/25本未満のスキップを成功0件とする |
| 日本株PER条件 | 対応済み条件なら標準JSON優先。既存PERサンプルと20件へ変更した定義をオフラインSchema検証 | 不要なPython/BATや未知のfilter。ランキング取得を全件とする |
| 出来高上位100件確定後1h RSI14 | 母集団→日足出来高順位→100件のみ1h RSI14の順。単一JSONの多段処理は未対応、Python候補でもデータ対応を先に確認 | RSI先行フィルタ、日足RSIへの代替、先頭1000件だけで市場全体を保証 |
| 全米株・条件なし・全件 | 現行のProvider制約・最大1000行・全件列挙引数なしを説明し、完全成功を防止 | S&P 500/先頭1000件へ縮小して全米株成功、失敗を0件成功とする |

これらはガイドによる判定可能性の確認であり、モデル出力の自動回帰テストや実データの再現結果ではありません。`screen_prime_sma25.py`・`run-prime-sma25.bat`の修理、実行、新規製品追加はしていません。

## 自動読込：公式仕様と現環境の実証範囲

| 製品 | 仕様と確認方法 | 現環境の結果・未検証事項 |
| --- | --- | --- |
| Gemini CLI | 既定GEMINI.mdをワークスペース/親階層等から読込。ルートで起動し`/memory show`で確認 | `Get-Command gemini`はNOT_FOUND。静的導線と公式仕様のみ確認、実セッション・IDE・回帰入力は未検証 |
| Codex | 起動時にルート→作業場所のAGENTS.mdを探索。同階層override・サイズ上限等に依存 | `codex --version`で0.163.0-alpha.10.2。main作業ルートで下記起動を試行したが状態DBアクセス拒否・in-process app-server初期化失敗、exit 1。入口認識・モデル応答まで未到達。developで同じ起動の反復はせず、両ブランチの自動読込実証は未検証 |
| Claude Code | 作業場所と親階層のCLAUDE.md等を起動時に読込。`/memory`/`/context`で確認 | `Get-Command claude`はNOT_FOUND。静的導線と公式仕様のみ確認、実セッション・IDE・回帰入力は未検証 |

起動試行：`codex exec --ephemeral --ignore-user-config --sandbox read-only --json <起動時の指示だけを報告し、Tool/編集を禁止するプロンプト>`。ユーザー設定を除外した限定試行で、認証・設定ファイルを編集していません。現在のチャットで手動閲覧したファイルを、新規Codexの自動読込証跡にはしません。

公式根拠：[Gemini CLI](https://geminicli.com/docs/cli/gemini-md/)、[Codex](https://developers.openai.com/codex/guides/agents-md)、[Claude Code](https://code.claude.com/docs/en/memory)。通常のAIチャットにフォルダ名だけを送った場合の自動適用を約束せず、入口のMarkdownリンクから共通ガイド全文が自動展開されるとも扱いません。

## 実施した検証と制約

- 既存の追跡ファイルから文書チェックツールを探索したが、専用ツールは見つからなかった。依存を追加せず、一時的なNode標準ライブラリの検査で変更Markdownの相対リンク・アンカー、各入口→共通ガイド、正式BATパス、Markdownのみの差分を確認した。検査コードは配布・commitに含めない。
- mainの変更8文書について相対リンク111件・アンカー16件に合格。全treeの`tests/`・`docs/development/`・`docs/archive/`・`.codex/`・`.claude/`・`scripts/development/`・`requirements-dev.txt`不存在、短い入口本文に開発設定・役割指示がないことを確認した。
- developの変更11文書について相対リンク124件・アンカー20件に合格。既存AGENTS/CLAUDE本文から今回の追加節とBATパス訂正だけを除いた文字列が基点と一致することを確認し、開発規則の保持を検証した。
- `app.bat --help`はexit 0。正式`scripts/setenv.bat`経由のEmbedded PythonでPER同梱定義（limit 5）とlimit 20の派生定義、Read-only Jobの参照、Request上限1000・offset/pageなし・日足OHLCVのRequestをオフライン検証した。実行Pythonがプロジェクトruntime配下であることも確認した。
- ガイドの主張をScreening/Job/Provider Request、engine、normalization、results、同梱JSON、現BATおよび[公式Provider資料](https://www.tradingview.com/mcp/docs)と照合した。Schemaが任意文字列を許すことをProvider対応の証明にしない。
- 両ブランチで`git diff --check`に合格。共通5文書の同一性、develop既存入口の保持も確認した。PR作成後のbase/headと変更ファイルの確認は各PR本文の最終記録で補う。
- Provider実接続・列Discovery・実銘柄取得は未実行。プライム全件/SMA25対応は未確認であり、全件取得成功を主張しない。認証情報変更・Watchlist/Alert Write・Scheduler登録/削除は行っていない。
- 文書のみのため全件pytest/ruffやDocker再buildは実施しない。Gemini/Claudeの導入、認証環境の変更、ZIP生成/展開、Public化、tag/Releaseも実施しない。

[ブランチ運用](BRANCH_WORKFLOW.md) / [共通ガイド](../user/AI_JSON_GUIDE.md)
