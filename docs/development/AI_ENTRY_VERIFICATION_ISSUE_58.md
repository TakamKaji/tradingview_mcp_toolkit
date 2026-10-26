# Issue #58：AI入口・判定契約の検証記録

対象：[Issue #58](https://github.com/TakamKaji/tradingview_mcp_support/issues/58)。2026-10-25 JST実施。基点はmain `dace57a`、develop `b56a4ae`。これは文書・入口の検証であり、3製品の遵守やProviderの実取得成功を保証するものではありません。

最新の調査順序・運用変更は末尾「調査順序とdevelop-firstへの統一」に記載する。main先行・両PR同期の記述は過去の作業履歴であり、現行の運用正本は[ブランチ運用](BRANCH_WORKFLOW.md)、Screening規則の正本は[共通ガイド](../user/AI_JSON_GUIDE.md)とする。

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
| 開発設定を配布しない、PR運用 | 初回はmain/develop別PRで共通文書と入口を分離。現在はdevelop向けPRを原則1本とし、マージ後に必要時のみ配布を選択的に同期する。mainへの開発資産混入・自動merge・公開・tag/Releaseは禁止 |

## 自然言語入力に対する静的回帰レビュー

| ケース | 確認した期待判断 | 不合格として検出すべき応答 |
| --- | --- | --- |
| 東証プライム全体SMA25乖離率+20%以上 | まずScreener直接対応と市場/期間/日時を調べ、可能ならJSON。不可なら既存Readの候補・直接指標・一括取得、必要時だけOHLCV計算。母集団を確定できない場合だけ外部一覧。実用可能なPythonの作成・依頼された実行と完全性報告を分ける | 調査前からJPX必須・全銘柄OHLCV取得を前提にする。上位100件＋代表銘柄で代替。応答構造・NaN・途中中断を無視して全件成功とする |
| 日本株PER条件 | 対応済み条件なら標準JSON優先。既存PERサンプルと20件へ変更した定義をオフラインSchema検証 | 不要なPython/BATや未知のfilter。ランキング取得を全件とする |
| 出来高上位100件確定後1h RSI14 | 母集団→日足出来高順位→100件のみ1h RSI14の順をPythonで実装。直接指標取得または1h OHLCVからの計算を調べ、未取得による順位/判定の不完全さを報告 | RSI先行フィルタ、日足RSIへの代替、先頭1000件だけで市場全体を保証。直接指標がないだけでOHLCV計算を諦める |
| 全米株・条件なし・全件 | 標準Screenerの既知制約を維持し、既存Readによる母集団確定を先に調べ、できない場合だけ同じ全米株定義の外部一覧と分割取得を検討。完全取得は未保証と明記 | S&P 500/先頭1000件へ縮小して全米株成功、失敗を0件成功とする。Screener制約を全ラッパーの禁止とする |

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

## 2026-10-26：方式Bの動作方針改定

PR #59・#60は修正開始時にマージ済みだったため、最新main `b7ecd7e`・develop `accb3c5`から後続ブランチを作成した。元PRの本文へ後続の追跡先を追記し、今回のPRはマージしない。上表の回帰判断も本改定に合わせて更新した。前節までの初回の検査件数・実起動の制約は2026-10-25の記録として残す。

- 共通変更はAI_JSON_GUIDE、AI_USAGE、README日英の4文書。mainの`541f0a4`をdevelopへ`cherry-pick -x`した`fa15fe8`で同期した。既存のAI入口・開発規則・productionコードは変更しない。本記録の更新はdevelop専用コミットに分離する。
- JSON優先を保ち、JSONで表せない時は既存TradingViewClient/型付きRequestを調査してPythonを作成する方針を確認。get_ohlcv/get_symbol_data_batch/get_screener_columns等のReadと外部母集団・Pythonのデータ処理を組み合わせる。別途AIへの公式MCP登録、独自MCP/OAuth/TradingView HTTP再実装、別MCPライブラリ・非公式API導入は禁止する。
- [東証プライムの組立手順](../user/AI_JSON_GUIDE.md#東証プライムsma25乖離率の組立手順)に公式JPX一覧、シンボル対応付け、既存日足取得、SMA25/乖離率のローカル計算、欠損/未取得/エラー/対象日時、保存・正確な起動と確認方法を記載。事前の全件保証を作成の必須条件とせず、部分結果の完全成功報告を防ぐ。直接Screenerの未対応と方式Bの可能性を区別する。
- 実ファイルの保存先、実行環境、正確な実行コマンド、結果保存先を提示し、実行依頼と環境があれば実行・検証、利用不能なら理由と未実行状態を示す契約を確認した。条件固有スクリプトを今回の文書修正で製品へ追加したという意味ではない。
- mainは変更4文書と入口3文書の相対リンク99件/アンカー14件、developは変更5文書と入口3文書の相対リンク106件/アンカー17件に合格。3入口の導線、正式BAT5パス、変更範囲、共通4文書の同一性、git diff --checkも合格。mainの開発専用ファイル不存在、developの開発入口/設定無変更を確認した。
- Embedded Pythonでget_ohlcv/get_symbol_data_batch/get_screener_columns/search_symbolsの非同期関数と引数契約、対応Request、非同期コンテキストをオフライン照合した。Client生成・MCP接続は行わず、依存追加もない。JPX公式一覧ページの配布基準時点を確認したが、実銘柄一覧の取込・シンボル照合・OHLCV実取得・モデル遵守は未検証。
- 文書変更のため全件pytest/ruff・Docker再buildは実施しない。認証情報・Watchlist/Alert・Schedulerを変更せず、初回のAI自動読込実証を今回完了したとも扱わない。

## 2026-10-26：調査順序とdevelop-firstへの統一

既存PR #62のbaseはdevelop、headは`codex/issue-58-python-guide-develop`、開始時HEADは`10f324a`。既存の配布可能コミット`fa15fe8`と開発検証記録`10f324a`を保持して、同じheadへ今回の変更を追加する。mainは`b7ecd7e`のまま変更せず、PR #61には一本化の理由と後日の取り込み方針を本文・コメントへ残して、マージせずCloseする。新規PRは作成しない。

- 配布可能な変更は共通ガイド・AI_USAGE・README日英の4文書で、`de5f21c`に分離した。Screener直接取得→既存Readの組合せ→母集団を確定できない場合だけ外部一覧、の順序を正本へ明記し、要約文書を最小限で整合させた。将来mainへ配布する場合はPR #62のマージ後に`fa15fe8`→`de5f21c`を順に選択し、元のmain側`541f0a4`を重複適用しない。開発記録`10f324a`と今回の運用/検証コミットは配布しない。
- develop専用の変更はAGENTSのブランチ同期節、BRANCH_WORKFLOW、本検証記録。開発/文書ともdevelop起点、原則1PR内で実装・検証・レビュー、マージ後に必要時のみ選択的配布へ改定した。モデル役割分担・実装/テスト契約は保持した。
- Prime/SMA25の直接指定・列のfilter利用・期間/日時/市場への適合は、現環境ではProvider実取得による確認をしていない。対応済みとも不可能とも断言せず、候補取得の取りこぼし、ignored_filters・件数/coverageを確認する判断とした。4回帰ケースは上表の静的判断で確認する。
- 公式Provider資料と既存7 Read関数・Request・Response、Screener正規化の契約を照合した。Embedded Pythonのオフラインfixtureで型付き応答のProvider失敗とignored_filtersの拒否を確認した。ObservedReadResponseの包絡とTool別追加データを区別し、実OHLCV配列の格納場所・日時/値の構造を未確認のまま決めつけない。NaN/Inf・欠損・重複・基準日・価格調整、中断時の途中結果と未評価範囲を検証する規則を追加した。
- 変更7文書とCLAUDE/GEMINI/公開前チェックの計10文書で相対リンク115件・アンカー19件に合格。3入口の導線、正式BAT5パスとPython起動手順、git diff --check、AGENTSの運用節以外とCLAUDE/GEMINI/開発設定の保持、production/Schema/認証/通信/CLI/BAT/依存の無変更も確認した。PR #62の最終状態・push済みSHAとPR #61のClose結果はPR本文へ記録する。
- 条件固有のPython/BAT・汎用CLI・ワークフローエンジンは追加しない。ProviderライブRead・各AIへの入力/自動読込、全件pytest・Docker再buildは未実施。認証情報変更・Watchlist/Alert Write・Scheduler操作・main同期・マージ・公開・tag/Releaseは行わない。

[ブランチ運用](BRANCH_WORKFLOW.md) / [共通ガイド](../user/AI_JSON_GUIDE.md)
